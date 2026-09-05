#!/usr/bin/env bash
# Fixture seed. The required list is what the gate reads.
set -euo pipefail
python3 - <<PY
required = {
    "registers": ["demoapp"],
    "schemas": [        'task', 'project', 'plannedTimeEntry',
],
}["schemas"]
PY
