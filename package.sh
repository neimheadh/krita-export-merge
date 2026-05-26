#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

OUT="merge_groups.zip"
rm -f "$OUT"

zip -r "$OUT" merge_groups merge_groups.desktop \
    -x '*/__pycache__/*' '*.pyc'

echo "Created $OUT"
