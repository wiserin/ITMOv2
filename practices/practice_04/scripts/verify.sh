#!/usr/bin/env bash
set -euo pipefail

# Move to project root (directory of this script is scripts/)
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="${SCRIPT_DIR%/scripts}"

cd "$PROJECT_ROOT"

make test
exit $?
