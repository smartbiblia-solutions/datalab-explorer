#!/usr/bin/env bash
# Copy a pinned keshif-plus-custom build into static/keshif/.
# Usage: bash scripts/update-keshif.sh <commit-sha-or-tag>
set -euo pipefail
cd "$(dirname "$0")/.."
ref="${1:?usage: update-keshif.sh <commit-sha-or-tag>}"
repo="https://github.com/smartbiblia-solutions/keshif-plus-custom"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
git -C "$tmp" init -q
git -C "$tmp" fetch -q --depth 1 "$repo" "$ref"
git -C "$tmp" checkout -q FETCH_HEAD
rm -rf static/keshif
mkdir -p static/keshif
cp -R "$tmp"/dist/. static/keshif/
cp "$tmp"/LICENSE "$tmp"/NOTICE.md static/keshif/
echo "$repo $(git -C "$tmp" rev-parse HEAD)" > static/keshif/VERSION
echo "Installed $(cat static/keshif/VERSION)"
