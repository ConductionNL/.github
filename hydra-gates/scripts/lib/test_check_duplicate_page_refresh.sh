#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# gate-104 (duplicate-page-refresh) — checker acceptance over planted trees.
#
# 🔴 ARM 5 AND ARM 6 ARE THE LOAD-BEARING ONES.
#
# Arm 5 plants the word "Refresh" in an HTML comment and nowhere else. The
# first version of this checker would have failed it: the fix for THIS gate
# adds a comment to every surface it touches, explaining why Refresh is not
# repeated there, so a checker that greps raw text flags the very files it
# just cleaned. Comments are stripped before the Vue scan.
#
# Arm 6 plants an NcButton whose own `<template #icon>` sits between the slot
# opening and the Refresh label. `</template>` closes the ICON first, so a scan
# that matches to the nearest close reads an empty slot and reports clean over
# a real duplicate. The block scan counts depth.
#
# Arm 7 is the .github#374 rule: an empty scope must not print the same word as
# a clean full-tree read. Arm 8 is its complement — seven fleet apps ship
# dashboard pages that declare NO action list, and counting only pages that
# have one reported "checked 0" over them, indistinguishable from an app with
# no pages at all.
#
# Run: bash hydra-gates/scripts/lib/test_check_duplicate_page_refresh.sh

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
CHECKER="${SCRIPT_DIR}/check_duplicate_page_refresh.py"

_fail_n=0
_ok()  { printf '  ok   — %s\n' "$1"; }
_bad() { _fail_n=$((_fail_n + 1)); printf '  FAIL — %s\n' "$1"; }

WORK="$(mktemp -d "${TMPDIR:-/tmp}/gate104-dpr.XXXXXXXX")"
trap 'rm -rf "${WORK}"' EXIT

# _arm <name> <expected-rc> <expected-min-checked>
# Runs the checker over ${WORK}/<name> and asserts the exit code, plus that the
# terminal summary counted at least N surfaces. The count matters: an arm that
# expects PASS while having inspected nothing is the defect, not the control.
_arm() {
    local name="$1" want_rc="$2" want_min="$3"
    local out rc checked
    out="$(python3 "${CHECKER}" "${WORK}/${name}" 2>&1)"
    rc=$?
    checked="$(printf '%s\n' "${out}" | sed -n 's/^checked \([0-9]\{1,\}\) page surface.*/\1/p' | tail -1)"
    case "${checked}" in ''|*[!0-9]*) checked=0 ;; esac

    if [ "${rc}" -ne "${want_rc}" ]; then
        _bad "${name}: expected rc=${want_rc}, got rc=${rc}"
        printf '%s\n' "${out}" | sed 's/^/         /'
        return
    fi
    if [ "${checked}" -lt "${want_min}" ]; then
        _bad "${name}: expected at least ${want_min} surface(s) inspected, got ${checked}"
        printf '%s\n' "${out}" | sed 's/^/         /'
        return
    fi
    _ok "${name} (rc=${rc}, checked ${checked})"
}

_manifest() {  # <dir> <config-body>
    mkdir -p "${WORK}/$1/src"
    cat > "${WORK}/$1/src/manifest.json" <<JSON
{
  "id": "fixture",
  "pages": [
    { "id": "Dashboard", "route": "/", "type": "dashboard", "config": { $2 } }
  ]
}
JSON
}

_vue() {  # <dir> <file-body>
    mkdir -p "${WORK}/$1/src/views"
    printf '%s\n' "$2" > "${WORK}/$1/src/views/Fixture.vue"
}

echo "gate-104 duplicate-page-refresh — checker acceptance"

# --- ARM 1: the manifest duplicate -----------------------------------------
_manifest arm1 '"headerActions": [
      { "id": "new-thing", "type": "open-form", "label": "New thing" },
      { "id": "dashboard-refresh", "type": "refresh", "label": "Refresh" }
    ]'
_arm arm1 1 1

# --- ARM 2: the same manifest, opted out -----------------------------------
_manifest arm2 '"showRefresh": false,
    "headerActions": [
      { "id": "dashboard-refresh", "type": "refresh", "label": "Refresh" }
    ]'
_arm arm2 0 1

# --- ARM 3: the Vue duplicate ----------------------------------------------
_vue arm3 '<template>
	<CnDashboardPage :title="t(`app`, `Dashboard`)">
		<template #actions>
			<NcButton @click="reload">
				{{ t("app", "Refresh") }}
			</NcButton>
		</template>
	</CnDashboardPage>
</template>'
_arm arm3 1 1

# --- ARM 4: the same Vue surface, opted out --------------------------------
_vue arm4 '<template>
	<CnDashboardPage :title="t(`app`, `Dashboard`)" :showRefresh="false">
		<template #actions>
			<NcButton @click="reload">
				{{ t("app", "Refresh") }}
			</NcButton>
		</template>
	</CnDashboardPage>
</template>'
_arm arm4 0 1

# --- ARM 5: Refresh named only in a comment (the fix writes these) ----------
# The comment sits INSIDE the slot and contains markup that every matcher
# branch would otherwise hit — a `<Refresh>` tag and a quoted 'Refresh' label.
# Without comment stripping this arm fails, and it fails on precisely the
# shape this gate's own remedy leaves behind.
_vue arm5 '<template>
	<CnDashboardPage :title="t(`app`, `Dashboard`)" @refresh="reload">
		<template #actions>
			<!-- Refresh is NOT repeated here. The removed markup was
			     <NcButton :aria-label="t(`app`, `Refresh`)"><Refresh :size="20" /></NcButton>
			     and @refresh on the host now routes the menu item to reload. -->
			<NcButton @click="create">
				{{ t("app", "New thing") }}
			</NcButton>
		</template>
	</CnDashboardPage>
</template>'
_arm arm5 0 1

# --- ARM 6: a nested <template #icon> must not truncate the slot scan -------
_vue arm6 '<template>
	<CnDashboardPage :title="t(`app`, `Dashboard`)">
		<template #actions>
			<NcButton @click="create">
				<template #icon>
					<Plus :size="20" />
				</template>
				{{ t("app", "New thing") }}
			</NcButton>
			<NcButton @click="reload">
				<template #icon>
					<Refresh :size="20" />
				</template>
			</NcButton>
		</template>
	</CnDashboardPage>
</template>'
_arm arm6 1 1

# --- ARM 7: empty scope must not read as PASS ------------------------------
mkdir -p "${WORK}/arm7/src"
_arm arm7 4 0

# --- ARM 8: a dashboard page with no action list is still an inspected surface
_manifest arm8 '"description": "A dashboard that declares no header actions."'
_arm arm8 0 1

# --- ARM 9: "icon": "Refresh" on some other action is not a finding ---------
_manifest arm9 '"headerActions": [
      { "id": "renew-consent", "type": "api-call", "label": "Renew consent", "icon": "Refresh" }
    ]'
_arm arm9 0 1

echo ""
if [ "${_fail_n}" -eq 0 ]; then
    echo "gate-104 checker acceptance: ALL GREEN"
    exit 0
fi
echo "gate-104 checker acceptance: ${_fail_n} assertion(s) failed"
exit 1
