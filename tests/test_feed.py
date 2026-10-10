# SPDX-License-Identifier: AGPL-3.0
import hashlib
import json
from pathlib import Path
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


if __name__ == "__main__":
    unittest.main()
