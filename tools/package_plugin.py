#!/usr/bin/env python3
"""Package tracked source from one immutable Git commit, reproducibly."""
# SPDX-License-Identifier: AGPL-3.0
import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_STORED, ZipFile, ZipInfo

REPOSITORY = "https://github.com/rzp-labs/CommunityScripts"
BUILD_SOURCE = (
    "MAINTENANCE.md",
    "build_site.sh",
    "publication-plugins.txt",
    "tools/package_plugin.py",
    "tests/test_installer.py",
    "tests/test_feed.py",
)


def git(*args):
    return subprocess.check_output(["git", *args])


def package(plugin_dir, output):
    commit = git("rev-parse", "HEAD").decode().strip()
    prefix = plugin_dir.rstrip("/") + "/"
    paths = git("ls-tree", "-r", "--name-only", "-z", commit, "--", prefix)
    contents = {
        path[len(prefix):]: git("show", f"{commit}:{path}")
        for path in paths.decode().split("\0") if path
    }
    for path in BUILD_SOURCE:
        contents["source/" + path] = git("show", f"{commit}:{path}")
    contents["SOURCE.json"] = (json.dumps({
        "repository": REPOSITORY,
        "commit": commit,
        "plugin_path": plugin_dir,
        "source_url": f"{REPOSITORY}/tree/{commit}/{plugin_dir}",
        "corresponding_source_url": f"{REPOSITORY}/archive/{commit}.tar.gz",
        "license": "AGPL-3.0",
    }, indent=2, sort_keys=True) + "\n").encode()
    if "LICENSE" not in contents or "NOTICE.md" not in contents:
        raise RuntimeError("Package must contain LICENSE and NOTICE.md")
    with ZipFile(Path(output), "w", compression=ZIP_STORED) as archive:
        for name, data in sorted(contents.items()):
            info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)


if __name__ == "__main__":
    package(*sys.argv[1:])
