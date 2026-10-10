# PythonToolsInstaller source and license notice

This plugin comes from stashapp/CommunityScripts, licensed under the GNU Affero
General Public License, version 3 (AGPL-3.0). The full upstream license is in
`LICENSE`; upstream history and notices are retained in the public fork.

Upstream source baseline: `4130c96bcb435d296f5e3b32b3b1333aed9ee893`:
https://github.com/stashapp/CommunityScripts/tree/4130c96bcb435d296f5e3b32b3b1333aed9ee893/plugins/PythonToolsInstaller

Modified by nehpz <admin@rzp.one> on 2026-10-10, with Codex assistance: use the
created venv's interpreter for pip and package-path discovery, propagate failed
installs, preserve the JSON response, and record the copy destination correctly.
These modifications are distributed under AGPL-3.0. There is no warranty; see the
license for the complete terms.

Each distributed ZIP includes the plugin's corresponding Python source,
descriptor, requirements, license and this notice. `SOURCE.json` identifies the
exact full Git commit and immutable source/archive URLs. `source/` includes the
scripts controlling feed/package creation and their tests. The public fork also
provides the complete corresponding repository source and upstream history:
https://github.com/rzp-labs/CommunityScripts

`packages/stashtools.txt` retains upstream's unpinned `stashapp-tools` requirement.
Dependencies are obtained from pip at installation time and are not redistributed
in this plugin ZIP. Their versions depend on the package index and environment.

The install task still copies dependencies into the system interpreter's
site-packages. Container replacement can lose that system copy; running Install
again restores it. Persistence redesign is outside this repair.
