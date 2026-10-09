#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
printf 'GURUDEV.ai running at http://127.0.0.1:8502\n'
python -m gurudev_ai.companion.server
