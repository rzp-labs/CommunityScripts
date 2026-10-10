# SPDX-License-Identifier: AGPL-3.0
# Modified by nehpz <admin@rzp.one>, 2026-10-10:
# discover the venv package path and stop on pip failure. See NOTICE.md.
import shutil
import sys, json, sysconfig
from venv import create
from os.path import abspath
import subprocess

def main():
	input = None

	if len(sys.argv) < 2:
		input = readJSONInput()

	output = {}
	run(input, output)

	out = json.dumps(output)
	print(out + "\n")

def readJSONInput():
	input = sys.stdin.read()
	return json.loads(input)


def run(input, output):

	if input == "None" or input == "":
		return


	PLUGIN_DIR = input["server_connection"]["PluginDir"]
	modeArg = input['args']["mode"]

	if modeArg == "" or modeArg == "add":
		return

	elif modeArg == "process_py_stashapi_tools":
		get_download_py_stashapp_tools(PLUGIN_DIR)

	output["output"] = "ok"

def get_download_py_stashapp_tools(PLUGIN_DIR):

	org_packagedir = sysconfig.get_paths()["purelib"]

	used_dir = f"{PLUGIN_DIR}"
	create(f"{used_dir}/venv/", with_pip=True)

	venv_python = f"{used_dir}/venv/bin/python"
	# Use the same interpreter for pip and sysconfig; image versions/layouts can change.
	# Keep pip's progress on stderr so stdout remains the raw plugin JSON response.
	subprocess.run([venv_python, "-m", "pip", "install", "-r", abspath(f"{used_dir}/packages/stashtools.txt")], stdout=sys.stderr, check=True)
	src = subprocess.check_output([venv_python, "-c", "import sysconfig; print(sysconfig.get_paths()['purelib'])"], text=True).strip()
	if not src:
		raise RuntimeError("The venv interpreter returned an empty purelib path")
	destination = shutil.copytree(src, org_packagedir, ignore=ignore_func, dirs_exist_ok=True)
	with open(f'{used_dir}/copydo.txt', 'w+') as fp:
		fp.write("%s\n" % destination)

def ignore_func(src, names):
	return ['env'] if 'env' in names else []


if __name__ == "__main__":
	main()
