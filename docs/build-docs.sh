#!/usr/bin/env bash

set -e

# Exit script if you try to use an uninitialized variable.
set -o nounset

action=$1

# Move some files around. We need a separate build directory, which would
# have all the files, build scripts would shuffle the files,
# we don't want that happening on the actual code locally.
# When running on ReadTheDocs, sphinx-build would run directly on the original files,
# but we don't care about the code state there.
rm -rf docs/build
mkdir docs/build/
cp -r docs/_templates docs/conf.py docs/*.svg docs/*.json  docs/build/

if [ "$action" == "linkcheck" ]; then
  sphinx-build -c docs/ -WETan -j auto -D language=en -b linkcheck docs/build/ docs/build/html
elif [ "$action" == "docs" ]; then
  sphinx-build -c docs/ -WETa -j auto -D language=en docs/build/ docs/build/html
fi

# Clean up build artefacts
rm -rf docs/build/html/_sources

# Copy built HTML to temp directory, clean up build dir and replace with built docs only
rm -rf docs/temp
mkdir docs/temp/
mkdir docs/temp/html
cp -rf docs/build/html/* docs/temp/html

rm -rf docs/build
mkdir docs/build
mkdir docs/build/html
cp -rf docs/temp/html/* docs/build/html
rm -rf docs/temp
