#!/bin/sh
set -eu
cd "$(dirname "$0")"
if ! command -v python3 >/dev/null 2>&1 || ! python3 -c 'import PyQt5' 2>/dev/null; then
    printf '%s\n' 'Missing Python 3 or PyQt5. See README.md.' >&2
    exit 1
fi
exec python3 -m catgirl_pet.app
