# SPDX-License-Identifier: AGPL-3.0
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "installer", ROOT / "plugins/PythonToolsInstaller/PythonToolsInstaller.py"
)
installer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(installer)


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="installer path ")
        self.addCleanup(self.temp.cleanup)
        self.plugin = Path(self.temp.name)
        self.system = self.plugin / "system-packages"
        self.paths = SimpleNamespace(get_paths=lambda: {"purelib": str(self.system)})
        self.input = {
            "server_connection": {"PluginDir": str(self.plugin)},
            "args": {"mode": "process_py_stashapi_tools"},
        }

    def test_interpreter_reported_paths_are_used_without_version_assumptions(self):
        for layout in (
            "venv/lib/python3.13/site-packages",
            "venv/lib/python3.14/site-packages",
            "venv/custom purelib/packages",
        ):
            with self.subTest(layout=layout):
                source = self.plugin / layout
                source.mkdir(parents=True)
                (source / "probe.py").write_text(layout)
                with patch.object(installer, "create") as create, \
                     patch.object(installer, "sysconfig", self.paths), \
                     patch.object(installer.subprocess, "run") as pip, \
                     patch.object(installer.subprocess, "check_output", return_value=str(source) + "\n") as query:
                    output = {}
                    installer.run(self.input, output)
                python = str(self.plugin / "venv/bin/python")
                create.assert_called_once_with(str(self.plugin / "venv") + "/", with_pip=True)
                self.assertEqual(pip.call_args.args[0], [
                    python, "-m", "pip", "install", "-r",
                    str(self.plugin / "packages/stashtools.txt"),
                ])
                self.assertTrue(pip.call_args.kwargs["check"])
                self.assertIs(pip.call_args.kwargs["stdout"], sys.stderr)
                self.assertEqual(query.call_args.args[0][0], python)
                self.assertEqual((self.system / "probe.py").read_text(), layout)
                self.assertEqual((self.plugin / "copydo.txt").read_text(), str(self.system) + "\n")
                self.assertEqual(output, {"output": "ok"})

    def test_pip_failure_aborts_before_query_copy_and_success_response(self):
        failure = subprocess.CalledProcessError(1, ["python", "-m", "pip"])
        with patch.object(installer, "create"), \
             patch.object(installer, "sysconfig", self.paths), \
             patch.object(installer.subprocess, "run", side_effect=failure), \
             patch.object(installer.subprocess, "check_output") as query, \
             patch.object(installer.shutil, "copytree") as copy:
            output = {}
            with self.assertRaises(subprocess.CalledProcessError):
                installer.run(self.input, output)
            query.assert_not_called()
            copy.assert_not_called()
            self.assertEqual(output, {})
            self.assertFalse((self.plugin / "copydo.txt").exists())

    def test_failed_or_empty_path_query_does_not_copy(self):
        for result in (subprocess.CalledProcessError(2, ["python", "-c"]), "\n"):
            with self.subTest(result=result), \
                 patch.object(installer, "create"), \
                 patch.object(installer, "sysconfig", self.paths), \
                 patch.object(installer.subprocess, "run"), \
                 patch.object(installer.subprocess, "check_output") as query, \
                 patch.object(installer.shutil, "copytree") as copy:
                if isinstance(result, Exception):
                    query.side_effect = result
                else:
                    query.return_value = result
                with self.assertRaises((subprocess.CalledProcessError, RuntimeError)):
                    installer.run(self.input, {})
                copy.assert_not_called()

    def test_main_emits_only_json_on_success(self):
        with patch.object(installer.sys, "argv", ["PythonToolsInstaller.py"]), \
             patch.object(installer.sys, "stdin", io.StringIO(json.dumps(self.input))), \
             patch.object(installer, "get_download_py_stashapp_tools"), \
             contextlib.redirect_stdout(io.StringIO()) as stdout:
            installer.main()
        self.assertEqual(json.loads(stdout.getvalue()), {"output": "ok"})

    def test_copy_error_propagates(self):
        with patch.object(installer, "create"), \
             patch.object(installer, "sysconfig", self.paths), \
             patch.object(installer.subprocess, "run"), \
             patch.object(installer.subprocess, "check_output", return_value="/venv/packages\n"), \
             patch.object(installer.shutil, "copytree", side_effect=PermissionError):
            output = {}
            with self.assertRaises(PermissionError):
                installer.run(self.input, output)
            self.assertEqual(output, {})


class OfflineInstallTests(unittest.TestCase):
    def test_real_venv_pip_path_and_repeat_install(self):
        # Exercise real venv/pip twice, with an offline wheel and isolated destination.
        with tempfile.TemporaryDirectory(prefix="offline installer path ") as temp:
            plugin = Path(temp)
            packages = plugin / "packages"
            packages.mkdir()
            wheel = plugin / "installer_probe-1.0-py3-none-any.whl"
            metadata = "installer_probe-1.0.dist-info/"
            with ZipFile(wheel, "w") as archive:
                archive.writestr("installer_probe.py", "VALUE = 'installed offline'\n")
                archive.writestr(metadata + "METADATA", "Metadata-Version: 2.1\nName: installer-probe\nVersion: 1.0\n")
                archive.writestr(metadata + "WHEEL", "Wheel-Version: 1.0\nGenerator: installer-test\nRoot-Is-Purelib: true\nTag: py3-none-any\n")
                archive.writestr(metadata + "RECORD", "")
            (packages / "stashtools.txt").write_text(str(wheel) + "\n")
            destination = plugin / "system-packages"
            environment = {"PIP_NO_INDEX": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PIP_NO_CACHE_DIR": "1", "PIP_CONFIG_FILE": os.devnull}
            system_paths = SimpleNamespace(get_paths=lambda: {"purelib": str(destination)})
            with patch.dict(os.environ, environment), \
                 patch.object(installer, "sysconfig", system_paths):
                for attempt in (1, 2):
                    with self.subTest(attempt=attempt):
                        installer.get_download_py_stashapp_tools(str(plugin))
                        self.assertEqual((destination / "installer_probe.py").read_text(), "VALUE = 'installed offline'\n")
                        self.assertEqual((plugin / "copydo.txt").read_text(), str(destination) + "\n")
                        self.assertEqual(subprocess.check_output([
                            sys.executable, "-c",
                            "import sys; sys.path.insert(0, sys.argv[1]); import installer_probe; print(installer_probe.VALUE)",
                            str(destination),
                        ], text=True).strip(), "installed offline")
                        # Reinstall restores a lost system copy using the retained venv.
                        (destination / "installer_probe.py").unlink()


if __name__ == "__main__":
    unittest.main()
