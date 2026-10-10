#!/bin/bash
set -euo pipefail

# Builds the explicitly allowlisted maintained plugins using the upstream index format.
# outputs to _site with the following structure:
# index.yml
# <plugin_id>.zip
# Each ZIP contains tracked plugin source, license/notices, and build-source provenance.

outdir="${1:-_site}"
if [ -z "$outdir" ]; then
    outdir="_site"
fi

# Only package committed source; SOURCE.json must describe the bytes being shipped.
git diff --quiet HEAD -- build_site.sh tools tests publication-plugins.txt plugins/PythonToolsInstaller || {
    echo "Commit maintained plugin/build changes before packaging" >&2
    exit 1
}

rm -rf "$outdir"
mkdir -p "$outdir"

buildPlugin() 
{
    f=$1

    if grep -q "^#pkgignore" "$f"; then
        return
    fi
    
    # Preserve the runtime ID from the descriptor filename.
    dir=$(dirname "$f")
    plugin_id=$(basename "$f" .yml)

    echo "Processing $plugin_id"

    # SOURCE.json embeds HEAD, and root docs/build/tests are also shipped.
    # Every new source commit must therefore identify a distinct feed version.
    version=$(git rev-parse HEAD)
    updated=$(TZ=UTC0 git show -s --date="format-local:%F %T" --format=%cd "$version")
    
    # Create a deterministic archive from tracked files at this exact commit.
    zipfile="$outdir/$plugin_id.zip"
    
    python3 tools/package_plugin.py "$dir" "$zipfile"

    name=$(grep "^name:" "$f" | head -n 1 | cut -d' ' -f2- | sed -e 's/\r//' -e 's/^"\(.*\)"$/\1/')
    description=$(grep "^description:" "$f" | head -n 1 | cut -d' ' -f2- | sed -e 's/\r//' -e 's/^"\(.*\)"$/\1/')
    ymlVersion=$(grep "^version:" "$f" | head -n 1 | cut -d' ' -f2- | sed -e 's/\r//' -e 's/^"\(.*\)"$/\1/')
    version="$ymlVersion-$version"
    dep=$(grep "^# requires:" "$f" | cut -c 12- | sed -e 's/\r//' || true)

    # write to spec index
    echo "- id: $plugin_id
  name: $name
  metadata:
    description: $description
  version: $version
  date: $updated
  path: $plugin_id.zip
  sha256: $(sha256sum "$zipfile" | cut -d' ' -f1)" >> "$outdir"/index.yml

    # handle dependencies
    if [ ! -z "$dep" ]; then
        echo "  requires:" >> "$outdir"/index.yml
        for d in ${dep//,/ }; do
            echo "    - $d" >> "$outdir"/index.yml
        done
    fi

    echo "" >> "$outdir"/index.yml
}

while IFS= read -r file || [ -n "$file" ]; do
    [[ -z "$file" || "$file" == \#* ]] && continue
    if [[ ! "$file" =~ ^plugins/[A-Za-z0-9_-]+/[A-Za-z0-9_-]+\.yml$ ]]; then
        echo "Invalid publication allowlist entry: $file" >&2
        exit 1
    fi
    git ls-files --error-unmatch "$file" > /dev/null
    buildPlugin "$file"
done < publication-plugins.txt
test -s "$outdir/index.yml"
