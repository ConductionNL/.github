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

# Count apps whose appinfo/info.xml is actually READABLE inside the container.
# Counting `ls custom_apps/` instead is not enough: when a bind mount fails to
# attach, Docker still creates the mount-point directory, so the app dir exists
# but is EMPTY. That reported a healthy 39/39 while every app was in fact missing
# and the whole instance was 503'ing. Requiring info.xml proves content arrived.
visible_apps() {
  docker exec "$CONTAINER" sh -c \
    'n=0; for d in /var/www/html/custom_apps/*/; do [ -f "$d/appinfo/info.xml" ] && n=$((n+1)); done; echo "$n"' \
    2>/dev/null | tr -d '[:space:]'
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

echo "==> Ensuring un-busted assets are not cached for 6 months"
# Nextcloud's shipped .htaccess caches static assets for max-age=15778463 (6 months)
# EVEN WHEN the URL carries no ?v= cache buster. With 'debug' => true — which this
# dev instance runs — NC strips ?v= from every app script
# (TemplateLayout::getVersionHashSuffix() returns '' in debug mode), so every entry
# bundle lands in that branch: you deploy new JS and the browser keeps executing the
# old one, immutably, with no way to bust it. Assets that DO carry ?v= keep the long
# immutable cache, which is correct. ETag revalidation makes this cheap (304s).
# Lives in the /var/www/html volume, so re-apply on every start (idempotent).
if docker exec "$CONTAINER" sh -c '
  H=/var/www/html/.htaccess
  grep -q "no-cache, must-revalidate" "$H" && exit 0
  # Only the bare 6-month directive — the `, immutable` one (URLs that DO carry ?v=)
  # is correct and must be left alone. The `"$` anchor is what distinguishes them.
  sed -i "0,/Header set Cache-Control \"max-age=15778463\"$/s//Header set Cache-Control \"no-cache, must-revalidate\"/" "$H"
  # Verify, so an upstream reformat surfaces as a warning instead of silently no-opping.
  grep -q "no-cache, must-revalidate" "$H"
' >/dev/null 2>&1; then
  echo "  ok"
else
  echo "  WARNING: could not patch .htaccess cache headers — un-busted assets may cache for 6 months"
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
