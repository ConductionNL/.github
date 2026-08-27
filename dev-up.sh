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
# Everything below the compose call answers one question: "is this app actually
# usable?" -- because `occ app:enable` reporting success answers a much narrower
# one. An app enables successfully with no vendor/autoload.php and then fatals on
# every request; it enables successfully carrying a pre-rename JS bundle and then
# renders a blank page. Both were true of live apps here on 2026-08-27 while this
# script printed a clean bill of health, so it now checks the dependency tree and
# the frontend bundle as well as the enable flag.
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

# The Conduction app set is DERIVED from the compose file, never written out by
# hand. The hardcoded list that used to live here went stale through the iq
# rename and named ten app DIRECTORIES -- openconnector, docudesk, procest,
# larpingapp, scholiq, decidesk, doriath, hrmq, openbuild, softwarecatalog --
# where Nextcloud wanted app IDs: integriq, filinq, dossiq, larpinq, learniq,
# decidiq, keepiq, humaniq, buildiq, stackiq. A name that matches nothing is not
# an error here, it is a silent skip: the loop printed a healthy-looking
# "re-enabling petstore / ok" while eleven fleet apps sat disabled. That is how
# the whole fleet came up inactive after a reset on 2026-08-27.
#
# Deriving from the mounts cannot go stale, because a mount DESTINATION is the
# app id (Nextcloud resolves an app by its directory name), so adding a mount
# adds the app here for free. The discriminator is the SOURCE path shape:
# Conduction checkouts are siblings of .github (`../<dir>`) while pre-installed
# third-party apps come from `../openregister/custom_apps/<app>` and must not be
# auto-enabled -- the regex rejects any source containing a slash, which is
# exactly that distinction.
#
# `docker inspect` is deliberately NOT the source here: on Docker Desktop/WSL2
# seven of these mounts report an opaque /run/desktop/mnt/host/wsl/...<sha>
# source, so the same rule applied to the running container silently loses apps.
app_mounts() {  # emits "<host-dir> <app-id>" for every Conduction app mount
  grep -oE '^[[:space:]]*-[[:space:]]*\.\./[A-Za-z0-9._-]+:/var/www/html/custom_apps/[A-Za-z0-9_-]+$' "$COMPOSE_FILE" \
    | sed -E 's|^[[:space:]]*-[[:space:]]*\.\./||; s|:/var/www/html/custom_apps/| |' \
    | sort -u
}

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

compose_up() {
  # shellcheck disable=SC2086
  docker compose -p "$PROJECT" -f "$COMPOSE_FILE" up -d \
    ${PROFILES:+$(printf -- '--profile %s ' $PROFILES)} 2>&1
}

echo "==> Starting stack (project=$PROJECT)"
# The output is CAPTURED, not discarded. `docker compose up` failing used to be
# sent to /dev/null and, with no `set -e`, the script sailed on into an unbounded
# `until pg_isready` and hung there forever -- the one instrument that knew the
# stack had not started was the one being silenced.
UP_OUT="$(compose_up)"; UP_RC=$?
if [ "$UP_RC" -ne 0 ]; then
  printf '%s\n' "$UP_OUT" | sed 's/^/    /'
  # A stale ghcr.io credential makes a PUBLIC image unpullable: Docker sends the
  # dead token instead of falling back to anonymous, and the registry answers
  # "denied: denied" -- which reads exactly like "this image is private and you
  # have no access". On 2026-08-27 that single expired token stopped the entire
  # stack from starting; `docker logout ghcr.io` was the whole fix. Retry once
  # anonymously before believing the denial.
  if printf '%s' "$UP_OUT" | grep -qE 'ghcr\.io.*denied'; then
    echo "  ghcr.io denied a pull -- logging out (credentials may be stale) and retrying once"
    docker logout ghcr.io >/dev/null 2>&1 || true
    UP_OUT="$(compose_up)"; UP_RC=$?
    [ "$UP_RC" -ne 0 ] && printf '%s\n' "$UP_OUT" | sed 's/^/    /'
  fi
fi
if [ "$UP_RC" -ne 0 ]; then
  echo "==> ABORTING: the stack did not start (docker compose up exited $UP_RC)"
  exit 1
fi

echo "==> Waiting for the DB"
# Bounded on purpose. The unbounded version could not distinguish "Postgres is
# still initialising" from "the DB container was never created", and reported
# the second as the first, indefinitely.
DB_OK=0
for _ in $(seq 1 60); do
  if docker exec "$DB_CONTAINER" pg_isready -U oc_admin -d nextcloud >/dev/null 2>&1; then DB_OK=1; break; fi
  sleep 2
done
if [ "$DB_OK" -ne 1 ]; then
  echo "==> ABORTING: $DB_CONTAINER never became ready within 120s"
  docker ps -a --filter "name=$DB_CONTAINER" --format '    {{.Names}} {{.Status}}'
  exit 1
fi

# Which mounted app dirs have no readable info.xml, and WHY. An empty host
# checkout and a bind mount that failed to attach look identical inside the
# container -- both are an existing, empty directory -- but only one of them is
# fixed by restarting. Conflating them cost every startup a pointless container
# restart and then printed a "still partial ... check file sharing / disk space"
# warning about two empty git checkouts, which is how a warning that would
# matter gets trained out of you.
missing_apps() {
  docker exec "$CONTAINER" sh -c \
    'for d in /var/www/html/custom_apps/*/; do [ -f "$d/appinfo/info.xml" ] || basename "$d"; done' 2>/dev/null
}

# Every custom_apps mount, third-party ones included, as "<host-src> <app-id>".
# app_mounts() deliberately sees only the Conduction siblings; this one has to
# see all of them, because the source that goes missing is just as likely to be
# a nested ../openregister/custom_apps/<app> path.
all_mounts() {
  grep -oE '^[[:space:]]*-[[:space:]]*\.\./[A-Za-z0-9._/-]+:/var/www/html/custom_apps/[A-Za-z0-9_-]+$' "$COMPOSE_FILE" \
    | sed -E 's|^[[:space:]]*-[[:space:]]*\.\./||; s|:/var/www/html/custom_apps/| |' \
    | sort -u
}

report_missing() {
  local a src raced=0
  for a in $(missing_apps); do
    src="$(all_mounts | awk -v a="$a" '$2 == a {print $1}')"
    if [ -z "$src" ]; then
      echo "    $a: inside the container but not in $COMPOSE_FILE -- a leftover directory in the volume"
    elif [ ! -d "$HERE/../$src" ]; then
      # The dangerous one. `docker compose up` silently CREATES a missing bind
      # source, so this mounts cleanly on a fresh start and looks like an empty
      # app; `docker restart` then refuses to recreate it and takes the whole
      # container down with "no such file or directory" -> Exited (127). Never
      # restart on account of this -- restarting is precisely what breaks it.
      echo "    $a: MOUNT SOURCE MISSING -- ../$src does not exist on the host."
      echo "        Restarting the container will FAIL on this mount and stop it. Create the"
      echo "        directory or drop its line from $COMPOSE_FILE."
    elif [ -z "$(ls -A "$HERE/../$src" 2>/dev/null)" ]; then
      echo "    $a: EMPTY CHECKOUT at ../$src -- clone it or drop its mount; restarting cannot help"
    else
      echo "    $a: present on the host but not inside the container -- the bind mount did not attach"
      raced=$((raced+1))
    fi
  done
  return "$raced"
}

WANT="$(expected_apps)"; WANT="${WANT:-1}"
echo "==> Waiting for all $WANT app mounts inside the container"
if ! wait_for_apps "$WANT" 15; then
  report_missing; RACED=$?
  if [ "$RACED" -eq 0 ]; then
    echo "  every missing dir is an empty checkout, not a mount failure -- not restarting"
  else
    echo "==> $RACED mount(s) came up partial — restarting the container once to re-establish them"
    docker restart "$CONTAINER" >/dev/null
    until docker exec "$CONTAINER" sh -c 'test -d /var/www/html/custom_apps' 2>/dev/null; do sleep 2; done
    if ! wait_for_apps "$WANT" 20; then
      report_missing; RACED=$?
      [ "$RACED" -gt 0 ] && echo "  WARNING: $RACED still partial after a restart — check Docker Desktop file sharing / disk space"
    fi
  fi
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

HOST_UID="$(id -u)"; HOST_GID="$(id -g)"
FIX_IMAGE="$(docker inspect "$CONTAINER" --format '{{.Config.Image}}' 2>/dev/null || echo alpine)"

# Composer run inside a root container leaves root-owned files on the host, and a
# later host-side `composer install` then dies part-way with "Could not delete
# .../vendor/<pkg>/<file>" -- which leaves a HALF-extracted vendor tree that still
# has no autoload.php, so the symptom is a broken app rather than a failed
# command. Composer's own cache under ~/.cache/composer is hit by the same thing.
heal_ownership() {
  local target="$1"
  [ -e "$target" ] || return 0
  find "$target" ! -user "$HOST_UID" -print -quit 2>/dev/null | grep -q . || return 0
  echo "    healing root-owned files under ${target##*/}"
  docker run --rm -v "$target":/x "$FIX_IMAGE" chown -R "$HOST_UID:$HOST_GID" /x >/dev/null 2>&1
}

echo "==> Healing PHP dependencies (vendor/)"
# An app whose lib/AppInfo/Application.php require_once's vendor/autoload.php and
# has no vendor/ does NOT fail to enable -- `occ app:enable` reports success and
# the app then fatals on every request, logging only
# "include_once(...vendor/autoload.php): Failed to open stream". Eight apps were
# in that state after the 2026-08-27 reset. keepiq was the honest one: it needs a
# vendored class during its repair step, so it refused to enable outright with
# `Class "Ramsey\Uuid\Uuid" not found` -- the same defect, loud instead of silent.
if command -v composer >/dev/null 2>&1; then
  heal_ownership "${COMPOSER_HOME:-$HOME/.cache/composer}"
  while read -r dir app; do
    appdir="$HERE/../$dir"
    [ -f "$appdir/composer.json" ] || continue
    # Only apps that actually load an autoloader at boot are load-bearing here.
    grep -rqs 'vendor/autoload' "$appdir/lib/AppInfo/" 2>/dev/null || continue
    [ -f "$appdir/vendor/autoload.php" ] && continue
    echo "  $app: no vendor/autoload.php -- installing"
    heal_ownership "$appdir/vendor"
    # --ignore-platform-reqs is CORRECT here, not a shortcut: the host CLI runs
    # PHP 8.3 without ext-bcmath or ext-intl while the code runs on the
    # container's PHP 8.4 which has both, so composer's platform check is
    # measuring the wrong PHP entirely. Versions still come from composer.lock,
    # so nothing floats.
    if (cd "$appdir" && composer install --no-dev --no-interaction --no-progress \
          --ignore-platform-reqs >/dev/null 2>&1) && [ -f "$appdir/vendor/autoload.php" ]; then
      echo "    ok"
    else
      echo "    FAILED -- run: (cd $appdir && composer install --no-dev --ignore-platform-reqs)"
    fi
  done < <(app_mounts)
else
  echo "  WARNING: composer not on PATH -- cannot heal vendor/; apps missing it will fatal at boot"
fi

echo "==> Ensuring Conduction apps are enabled"
ENABLE_FAILED=0
while read -r dir app; do
  # An app dir with no info.xml is an EMPTY checkout, not an app. Docker still
  # creates the mount point, so it looks identical to a present-but-disabled app.
  if ! docker exec "$CONTAINER" test -f "/var/www/html/custom_apps/$app/appinfo/info.xml" 2>/dev/null; then
    echo "  SKIP $app -- empty checkout at ../$dir (nothing to enable)"
    continue
  fi
  # Read the app's own state rather than grepping a snapshot of the Disabled
  # block for a name: a name that is in NEITHER block -- which is what every
  # stale id was -- matched nothing and was skipped in silence.
  state="$(occ app:list --output=json 2>/dev/null \
    | python3 -c "import sys,json;d=json.load(sys.stdin);a='$app';print('enabled' if a in d.get('enabled',{}) else 'disabled' if a in d.get('disabled',{}) else 'unknown')" 2>/dev/null || echo unknown)"
  [ "$state" = "enabled" ] && continue
  echo "  enabling $app ($state)"
  if err="$(occ app:enable "$app" 2>&1)"; then
    echo "    ok"
  else
    ENABLE_FAILED=$((ENABLE_FAILED+1))
    echo "    FAILED: $(printf '%s' "$err" | tr '\n' ' ' | cut -c1-160)"
  fi
done < <(app_mounts)
[ "$ENABLE_FAILED" -gt 0 ] && echo "  $ENABLE_FAILED app(s) could not be enabled -- see the errors above"

echo "==> Re-reconciling upgrades (enabling an app can register a migration)"
# This ran only BEFORE the enable loop, which is the wrong side of it: every app
# that gets enabled here can register its own pending migration, so the script
# used to sign off with `needsDbUpgrade: true` -- an instance that occ considers
# mid-upgrade and that serves a 503 the moment anything trips maintenance mode.
if occ status 2>/dev/null | grep -q 'needsDbUpgrade: true'; then
  echo "  needsDbUpgrade=true → running occ upgrade"
  occ upgrade --no-interaction 2>&1 | grep -iE 'updated|successful|maintenance mode' | sed 's/^/    /'
  occ maintenance:mode --off >/dev/null 2>&1 || true
else
  echo "  no upgrade needed"
fi

echo "==> Checking frontend bundles match the app id"
# `occ app:enable` says nothing about JavaScript. templates/index.php calls
# Util::addScript($appId, $appId.'-main'), so after an app id rename the shipped
# js/<old-id>-main.js no longer answers to anything: the app is enabled, its
# routes return 200, and the page renders BLANK. Five apps were in exactly that
# state on 2026-08-27 (integriq/filinq/stackiq/larpinq/keepiq, still carrying
# openconnector-/docudesk-/softwarecatalog-/larpingapp-/doriath- bundles) and
# nothing in this script or in occ would have said so.
STALE_JS=0
while read -r dir app; do
  appdir="$HERE/../$dir"
  [ -f "$appdir/templates/index.php" ] || continue
  grep -qs 'addScript' "$appdir/templates/index.php" || continue
  # .mjs counts: apps built with Vite emit <id>-main.mjs and Util::addScript
  # resolves either extension. Insisting on .js reported a correctly-built app
  # as broken, which is the same failure as missing a broken one.
  { [ -f "$appdir/js/$app-main.js" ] || [ -f "$appdir/js/$app-main.mjs" ]; } && continue
  # Globbed rather than parsed out of `ls` (SC2012): the glob gives the names
  # directly, and an unmatched glob stays literal, which the -f test rejects.
  have=""
  for cand in "$appdir"/js/*-main.js "$appdir"/js/*-main.mjs; do
    [ -f "$cand" ] && { have="$(basename "$cand")"; break; }
  done
  STALE_JS=$((STALE_JS+1))
  echo "  $app: js/$app-main.js missing${have:+ (found $have -- stale, pre-rename)}"
  echo "    fix: (cd ../$dir && npm ci && npm run build)"
done < <(app_mounts)
[ "$STALE_JS" -eq 0 ] && echo "  ok"

echo "==> Done. Status:"
occ status 2>/dev/null | grep -iE 'installed:|version:|maintenance:|needsDb' | sed 's/^/    /'
echo "    apps visible:  $(visible_apps)/$WANT"
echo "    apps enabled:  $(occ app:list --output=json 2>/dev/null | python3 -c 'import sys,json;print(len(json.load(sys.stdin)["enabled"]))' 2>/dev/null || echo '?')"
[ "${ENABLE_FAILED:-0}" -gt 0 ] && echo "    ⚠ $ENABLE_FAILED app(s) failed to enable"
[ "${STALE_JS:-0}" -gt 0 ]      && echo "    ⚠ $STALE_JS app(s) need a frontend rebuild before their page renders"
echo "    UI: http://localhost:8080   (admin/admin)"
