#!/usr/bin/env bash
# Compatibility entry point; output is versioned JSONL.
set -euo pipefail
exec python3 -u "$(dirname -- "${BASH_SOURCE[0]}")/doctor.py" "$@"
