#!/bin/sh
#
# Renders the deployment artefacts into an app repository:
#
#   templates/app-deploy/render.sh <app-id> <path-to-app-repo>
#
# Writes the root Dockerfile and .dockerignore, the image's entrypoint hook,
# an evaluation docker-compose.yml, the Helm chart charts/<app-id>/ and the
# image workflow. The compose file goes to the repository root, or to
# docker/docker-compose.yml when the root already has a docker-compose.yml of
# its own (usually the developer stack, which is left untouched).
#
# A file is only overwritten when it came from this template, so running it
# again updates an app to the current template. Prints the README section to
# add by hand.
#
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
# SPDX-License-Identifier: EUPL-1.2

set -eu

[ $# -eq 2 ] || { echo "usage: $0 <app-id> <path-to-app-repo>" >&2; exit 2; }
app="$1"
repo="$2"
here="$(cd "$(dirname "$0")" && pwd)"
marker="templates/app-deploy"

case "$app" in
	*[!a-z0-9_]*|'') echo "!! '$app' is not a Nextcloud app id" >&2; exit 2 ;;
esac

declared="$(sed -n 's:.*<id>\([a-z0-9_]*\)</id>.*:\1:p' "$repo/appinfo/info.xml" | head -n 1)"
[ "$declared" = "$app" ] || { echo "!! $repo/appinfo/info.xml declares '$declared', not '$app'" >&2; exit 1; }

compose=docker-compose.yml
context=.
if [ -f "$repo/docker-compose.yml" ] && ! grep -q "$marker" "$repo/docker-compose.yml"; then
	compose=docker/docker-compose.yml
	context=..
fi

render() {
	src="$here/$1"
	dst="$repo/$2"
	if [ -e "$dst" ] && ! grep -q "$marker" "$dst"; then
		echo "!! $2 exists and did not come from this template; leaving it alone" >&2
		return 1
	fi
	mkdir -p "$(dirname "$dst")"
	sed -e "s|__APP_ID__|$app|g" \
		-e "s|__COMPOSE_FILE__|$compose|g" \
		-e "s|__BUILD_CONTEXT__|$context|g" \
		"$src" > "$dst"
	echo "   $2"
}

echo "==> rendering $app into $repo"
render Dockerfile Dockerfile
render .dockerignore .dockerignore
render docker/entrypoint-hooks/before-starting/10-image-apps.sh docker/entrypoint-hooks/before-starting/10-image-apps.sh
chmod 0755 "$repo/docker/entrypoint-hooks/before-starting/10-image-apps.sh"
render docker-compose.yml "$compose"
render "charts/__APP_ID__/Chart.yaml" "charts/$app/Chart.yaml"
render "charts/__APP_ID__/values.yaml" "charts/$app/values.yaml"
render "charts/__APP_ID__/templates/NOTES.txt" "charts/$app/templates/NOTES.txt"
cp "$here/charts/__APP_ID__/.helmignore" "$repo/charts/$app/.helmignore"
cp "$here/charts/__APP_ID__/.gitignore" "$repo/charts/$app/.gitignore"
render workflows/container-image.yml .github/workflows/container-image.yml

echo "==> README section:"
sed -e "s|__APP_ID__|$app|g" -e "s|__COMPOSE_FILE__|$compose|g" "$here/README-section.md"
