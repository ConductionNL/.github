#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# test_lib_commonjs_scope.sh: the JS helpers must run wherever the package is
# checked out, including under a directory whose package.json says
# "type": "module".
#
# Node decides whether a .js file is CommonJS or an ES module from the NEAREST
# package.json above it. hydra-gates shipped none, so a checkout under the
# Nextcloud server tree (its package.json is "type": "module") turned every
# helper into an ES module, and gate-53 died with
# "require is not defined in ES module scope" before judging anything.
# scripts/lib/package.json pins the type to commonjs.
#
# Run: bash scripts/lib/test_lib_commonjs_scope.sh
set -uo pipefail

LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
PKG_DIR="$(cd "${LIB_DIR}/../.." && pwd)"

_fails=0
_ok()  { echo "  PASS: $1"; }
_bad() { echo "  FAIL: $1"; _fails=$((_fails + 1)); }

work="$(mktemp -d "${TMPDIR:-/tmp}/hg-esm.XXXXXX")" || exit 1
trap 'rm -rf "${work}"' EXIT
printf '{ "type": "module" }\n' > "${work}/package.json"
mkdir -p "${work}/hydra-gates"
cp -r "${PKG_DIR}/scripts" "${work}/hydra-gates/scripts"

echo "== the JS helpers run under a parent package.json with \"type\": \"module\" =="

if [ -f "${work}/hydra-gates/scripts/lib/package.json" ]; then
	_ok "scripts/lib/package.json is present"
else
	_bad "scripts/lib/package.json is missing"
fi

# The three helpers gate-53 chains, each run the way the runner runs it.
fixture="${work}/hydra-gates/scripts/test-fixtures/manifest-validation/non-apphost.manifest.json"
err="${work}/err.txt"
for helper in check_manifest.js build_effective_manifest.js check_manifest_crossref.js; do
	case "${helper}" in
		check_manifest.js) args=("${fixture}") ;;
		*) args=(--help) ;;
	esac
	( cd "${work}" && node "${work}/hydra-gates/scripts/lib/${helper}" "${args[@]}" ) >/dev/null 2>"${err}"
	if grep -q 'require is not defined in ES module scope' "${err}"; then
		_bad "${helper} was loaded as an ES module"
		sed 's/^/         /' "${err}" | head -5
	else
		_ok "${helper} loads as CommonJS"
	fi
done

echo
[ "${_fails}" -eq 0 ] || { echo "== ${_fails} failed =="; exit 1; }
echo "== all passed =="
exit 0
