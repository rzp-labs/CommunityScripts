# SPDX-License-Identifier: AGPL-3.0
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = "4130c96bcb435d296f5e3b32b3b1333aed9ee893"
PLUGIN = "plugins/PythonToolsInstaller"


class FeedTests(unittest.TestCase):
    def test_runtime_descriptor_preserved_except_version_and_source_url(self):
        path = PLUGIN + "/PythonToolsInstaller.yml"
        original = subprocess.check_output(["git", "show", UPSTREAM + ":" + path], cwd=ROOT, text=True)
        candidate = (ROOT / path).read_text()
        normalized = candidate.replace("version: 0.1.4", "version: 0.1.3").replace(
            "https://github.com/rzp-labs/CommunityScripts/tree/main/", "https://github.com/stashapp/CommunityScripts/tree/main/"
        )
        self.assertEqual(normalized, original)

    def test_feed_contains_only_maintained_source_and_reproducible_package(self):
        with tempfile.TemporaryDirectory(prefix="feed-test-") as temp:
            site = Path(temp) / "stable"
            subprocess.run(["bash", "build_site.sh", str(site)], cwd=ROOT, check=True)
            self.assertEqual({p.name for p in site.iterdir()}, {"index.yml", "PythonToolsInstaller.zip"})
            index = (site / "index.yml").read_text()
            self.assertEqual([line for line in index.splitlines() if line.startswith("- id:")], ["- id: PythonToolsInstaller"])
            package = site / "PythonToolsInstaller.zip"
            first = package.read_bytes()
            self.assertIn("sha256: " + hashlib.sha256(first).hexdigest(), index)
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
            self.assertIn("  version: 0.1.4-" + commit + "\n", index)
            date = subprocess.check_output([
                "git", "show", "-s", "--date=format-local:%F %T", "--format=%cd", commit
            ], cwd=ROOT, env=dict(os.environ, TZ="UTC0"), text=True).strip()
            self.assertIn("  date: " + date + "\n", index)
            with ZipFile(package) as archive:
                self.assertEqual(set(archive.namelist()), {
                    "PythonToolsInstaller.py", "PythonToolsInstaller.yml", "packages/stashtools.txt",
                    "LICENSE", "NOTICE.md", "SOURCE.json", "source/MAINTENANCE.md",
                    "source/build_site.sh", "source/publication-plugins.txt", "source/tools/package_plugin.py",
                    "source/tests/test_installer.py", "source/tests/test_feed.py",
                })
                self.assertEqual(archive.read("LICENSE"), (ROOT / "LICENSE").read_bytes())
                self.assertEqual(archive.read("PythonToolsInstaller.py"), subprocess.check_output([
                    "git", "show", commit + ":" + PLUGIN + "/PythonToolsInstaller.py"
                ], cwd=ROOT))
                provenance = json.loads(archive.read("SOURCE.json"))
                self.assertEqual(provenance["commit"], commit)
                self.assertEqual(provenance["plugin_path"], PLUGIN)
                self.assertEqual(provenance["license"], "AGPL-3.0")
                self.assertEqual(provenance["corresponding_source_url"], "https://github.com/rzp-labs/CommunityScripts/archive/" + commit + ".tar.gz")
            subprocess.run(["bash", "build_site.sh", str(site)], cwd=ROOT, check=True)
            self.assertEqual(package.read_bytes(), first)
            self.assertEqual((site / "index.yml").read_text(), index)

    def test_root_packaged_inputs_and_provenance_commits_advance_feed_metadata(self):
        # Local fixture commits exercise the failure without changing the real checkout.
        with tempfile.TemporaryDirectory(prefix="feed-metadata-") as temp:
            fixture = Path(temp) / "repo"
            site = Path(temp) / "stable"
            subprocess.run(["git", "clone", "--quiet", "--shared", str(ROOT), str(fixture)], check=True)

            def git(*args, **kwargs):
                return subprocess.check_output(["git", *args], cwd=fixture, text=True, **kwargs).strip()

            def build():
                subprocess.run(["bash", "build_site.sh", str(site)], cwd=fixture, check=True, stdout=subprocess.DEVNULL)
                fields = dict(line.strip().split(": ", 1) for line in (site / "index.yml").read_text().splitlines() if line.startswith(("  version:", "  date:", "  sha256:")))
                return fields, (site / "PythonToolsInstaller.zip").read_bytes()

            original_plugin_commit = git("log", "-1", "--format=%H", "--", PLUGIN)
            previous_fields, previous_zip = build()
            # Each file is actually shipped outside the plugin directory. The last
            # case changes only HEAD provenance, with no working-tree source change.
            inputs = ["MAINTENANCE.md", "build_site.sh", "publication-plugins.txt",
                      "tools/package_plugin.py", "tests/test_installer.py", "tests/test_feed.py", None]
            for number, path in enumerate(inputs, 1):
                with self.subTest(path=path or "HEAD provenance only"):
                    if path:
                        with (fixture / path).open("a") as file:
                            file.write("\n# Metadata regression fixture\n")
                        git("add", path)
                    date = f"2026-10-11T00:00:{number:02d}+00:00"
                    environment = dict(os.environ,
                        GIT_AUTHOR_NAME="nehpz", GIT_AUTHOR_EMAIL="admin@rzp.one",
                        GIT_COMMITTER_NAME="nehpz", GIT_COMMITTER_EMAIL="admin@rzp.one",
                        GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date,
                    )
                    git("-c", "commit.gpgsign=false", "commit", "--quiet", "--allow-empty", "-m", "Metadata regression fixture", env=environment)
                    fields, package = build()
                    self.assertEqual(git("log", "-1", "--format=%H", "--", PLUGIN), original_plugin_commit)
                    self.assertNotEqual(package, previous_zip)
                    self.assertNotEqual(fields["version"], previous_fields["version"])
                    self.assertNotEqual(fields["date"], previous_fields["date"])
                    commit = git("rev-parse", "HEAD")
                    self.assertEqual(fields["version"], "0.1.4-" + commit)
                    self.assertEqual(fields["date"], f"2026-10-11 00:00:{number:02d}")
                    self.assertEqual(fields["sha256"], hashlib.sha256(package).hexdigest())
                    with ZipFile(site / "PythonToolsInstaller.zip") as archive:
                        self.assertEqual(json.loads(archive.read("SOURCE.json"))["commit"], commit)
                    previous_fields, previous_zip = fields, package

    def test_release_checkout_pins_event_commit_instead_of_resolving_tag_again(self):
        workflow = (ROOT / ".github/workflows/deploy.yml").read_text()
        refs = re.findall(r"^\s+ref:\s*(.+)$", workflow, flags=re.MULTILINE)
        self.assertEqual(refs, ["${{ github.sha }}"])


if __name__ == "__main__":
    unittest.main()
