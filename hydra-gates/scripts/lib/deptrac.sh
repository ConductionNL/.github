#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Conduction <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2
#
# Run deptrac on lib/ of an app with one config:
#
#   layers        the generic layering rules of a Nextcloud app (deptrac/layers.yaml next to
#                 this script)
#   FILE.yaml     any other deptrac config, such as the functional areas that deptrac_areas.py
#                 writes from the app's components file
#
# Usage: deptrac.sh <app> layers|FILE.yaml [--rev REV] [--out DIR]
#   --rev REV   analyse lib/ of that commit (exported with git archive) instead of the working tree
#   --out DIR   write deptrac-<config>.json to DIR: the violations per layer pair, summarised by
#               deptrac_summary.py
#
# Prints the violations per layer pair. Exits 0 whether or not deptrac finds violations; the
# numbers are the result, not a pass or fail.
#
# deptrac is not a dependency of hydra-gates. Each app installs it with bamarni/composer-bin-plugin
# in vendor-bin/deptrac/composer.json ({"require-dev": {"deptrac/deptrac": "^4.7"}}), then
# composer --working-dir=vendor-bin/deptrac install. DEPTRAC=/path/to/deptrac overrides the binary.

set -euo pipefail

usage="usage: deptrac.sh <app> layers|FILE.yaml [--rev REV] [--out DIR]"
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
app="$(cd "${1:?${usage}}" && pwd)"
config_arg="${2:?${usage}}"
shift 2
rev=""
out=""
while [ "$#" -gt 0 ]; do
	case "$1" in
		--rev) rev="$2"; shift 2 ;;
		--out) out="$2"; shift 2 ;;
		*) echo "unknown argument: $1" >&2; exit 2 ;;
	esac
done

if [ "${config_arg}" = "layers" ]; then
	config="${here}/deptrac/layers.yaml"
else
	config="$(cd "$(dirname "${config_arg}")" && pwd)/$(basename "${config_arg}")"
fi
name="$(basename "${config}" .yaml)"
deptrac="${DEPTRAC:-${app}/vendor-bin/deptrac/vendor/bin/deptrac}"

[ -x "${deptrac}" ] || { echo "deptrac is not installed: composer --working-dir=${app}/vendor-bin/deptrac install" >&2; exit 2; }
[ -f "${config}" ] || { echo "no config ${config}" >&2; exit 2; }
[ -d "${app}/lib" ] || { echo "no lib/ in ${app}" >&2; exit 2; }

work="$(mktemp -d)"
trap 'rm -rf "${work}"' EXIT
if [ -n "${rev}" ]; then
	git -C "${app}" archive "${rev}" lib | tar -x -C "${work}"
else
	ln -s "${app}/lib" "${work}/lib"
fi
cp "${config}" "${work}/deptrac.yaml"

"${deptrac}" analyse --config-file="${work}/deptrac.yaml" --cache-file="${work}/.deptrac.cache" --no-progress \
	--formatter=json --output="${work}/report.json" >/dev/null || true
[ -s "${work}/report.json" ] || { echo "deptrac wrote no report" >&2; exit 1; }
summary=()
if [ -n "${out}" ]; then
	mkdir -p "${out}"
	summary=(--out "${out}/deptrac-${name}.json")
fi
python3 "${here}/deptrac_summary.py" "${work}/report.json" "${summary[@]}"
