#!/usr/bin/env bash
#
# dev-up.sh — deterministic, self-healing start for the Conduction dev instance.
#
# Why this exists: Docker Desktop / WSL2 bind mounts of the app tree can come up
# PARTIAL after a `docker stop/start`, and pre-installed apps carry WIP version
# bumps in their info.xml that trip Nextcloud's `needsDbUpgrade` → 503. The flat
# per-app mounts in docker-compose.yml fixed the "apps vanish" half; this script
# handles the rest: it waits for every mounted app to actually be visible inside
# the container (restarting once if a mount raced), clears maintenance mode, runs
# the pending upgrade only when needed, and re-enables any Conduction app that
# Nextcloud disabled. Run this instead of a bare `docker compose up`.
#
# Usage:  ./.github/dev-up.sh            # start + heal the default (postgres) stack
#         PROFILES="ai exapps" ./.github/dev-up.sh   # extra compose profiles
#
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$HERE/docker-compose.yml"
PROJECT="openregister"
CONTAINER="nextcloud"
DB_CONTAINER="conduction-postgres"

occ() { docker exec -u www-data "$CONTAINER" php occ "$@"; }

# Conduction apps that must be enabled for the instance to be usable. If Nextcloud
# disabled one (e.g. after a transient missing-code boot), we re-enable it.
CONDUCTION_APPS=(
  openregister opencatalogi openconnector openbuild softwarecatalog nldesign
  launchpad docudesk procest pipelinq zaakafhandelapp larpingapp scholiq hermiq
  decidesk doriath hrmq portaliq shillinq petstore
)

# Expected app dir count = number of bind mounts into custom_apps on the RUNNING
# container (authoritative for the active profile; self-corrects as apps are
# added). Read after `up -d` so it reflects what Docker actually attached.
expected_apps() {
  docker inspect "$CONTAINER" --format '{{range .Mounts}}{{println .Destination}}{{end}}' 2>/dev/null \
    | grep -cE '/var/www/html/custom_apps/[A-Za-z0-9_-]+$'
}

visible_apps() {
  docker exec "$CONTAINER" sh -c 'ls /var/www/html/custom_apps/ 2>/dev/null | wc -l' 2>/dev/null | tr -d '[:space:]'
}

wait_for_apps() {
  local want="$1" tries="${2:-15}" have=0
  for _ in $(seq 1 "$tries"); do
    have="$(visible_apps)"
    [ -n "$have" ] && [ "$have" -ge "$want" ] && { echo "  all $have/$want app dirs visible"; return 0; }
    sleep 2
  done
  echo "  only $have/$want app dirs visible"
  return 1
}

echo "==> Starting stack (project=$PROJECT)"
# shellcheck disable=SC2086
docker compose -p "$PROJECT" -f "$COMPOSE_FILE" up -d ${PROFILES:+$(printf -- '--profile %s ' $PROFILES)} >/dev/null

echo "==> Waiting for the DB"
until docker exec "$DB_CONTAINER" pg_isready -U oc_admin -d nextcloud >/dev/null 2>&1; do sleep 2; done

WANT="$(expected_apps)"; WANT="${WANT:-1}"
echo "==> Waiting for all $WANT app mounts inside the container"
if ! wait_for_apps "$WANT" 15; then
  echo "==> Mount came up partial — restarting the container once to re-establish it"
  docker restart "$CONTAINER" >/dev/null
  until docker exec "$CONTAINER" sh -c 'test -d /var/www/html/custom_apps' 2>/dev/null; do sleep 2; done
  wait_for_apps "$WANT" 20 || echo "  WARNING: still partial after a restart — check Docker Desktop file sharing / disk space"
fi

echo "==> Ensuring custom_apps is writable by www-data"
# Docker (re)creates the mount-parent dir as root:root, which leaves Nextcloud
# with no writable apps path → /settings/apps 500s ("Cannot write into apps
# directory"). Non-recursive on purpose: the per-app bind mounts inside keep
# their host ownership.
docker exec "$CONTAINER" chown www-data:www-data /var/www/html/custom_apps \
  && echo "  ok" || echo "  WARNING: chown failed — /settings/apps may 500"

echo "==> Clearing maintenance mode"
occ maintenance:mode --off >/dev/null 2>&1 || true

echo "==> Reconciling pending app upgrades (only if needed)"
if occ status 2>/dev/null | grep -q 'needsDbUpgrade: true'; then
  echo "  needsDbUpgrade=true → running occ upgrade"
  occ upgrade --no-interaction 2>&1 | grep -iE 'updated|successful|maintenance mode' | sed 's/^/    /'
  occ maintenance:mode --off >/dev/null 2>&1 || true
else
  echo "  no upgrade needed"
fi

echo "==> Ensuring Conduction apps are enabled"
DISABLED="$(occ app:list 2>/dev/null | sed -n '/Disabled:/,$p')"
for app in "${CONDUCTION_APPS[@]}"; do
  if printf '%s\n' "$DISABLED" | grep -q " - $app:"; then
    echo "  re-enabling $app"
    occ app:enable "$app" >/dev/null 2>&1 && echo "    ok" || echo "    FAILED (check its code/version)"
  fi
done

echo "==> Done. Status:"
occ status 2>/dev/null | grep -iE 'installed:|version:|maintenance:|needsDb' | sed 's/^/    /'
echo "    apps visible: $(visible_apps)/$WANT"
echo "    UI: http://localhost:8080   (admin/admin)"
