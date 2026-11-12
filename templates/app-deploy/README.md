# App deployment template

One set of deployment artefacts for every Conduction Nextcloud app, parameterised by the app id only:

| File in the app | What it is |
|---|---|
| `Dockerfile` | Evaluation image: the official Nextcloud image (pinned) with the app built from the repository and OpenRegister from its release, checked against the release SHA-256. Nothing secret is baked in. |
| `.dockerignore` | Keeps local `node_modules` and `vendor` out of the build. |
| `docker/entrypoint-hooks/before-starting/10-image-apps.sh` | Entrypoint hook: on every start, copies a newer baked app over the persistent copy, runs `occ upgrade` when needed and enables OpenRegister and the app. |
| `docker-compose.yml` | Nextcloud from that image, PostgreSQL and Redis, with every setting documented in the file. Written to `docker/docker-compose.yml` instead when the app already has a root `docker-compose.yml`, which is then left alone. |
| `charts/<app>/` | Helm chart over the official [Nextcloud chart](https://github.com/nextcloud/helm), running the same image with PostgreSQL. |
| `.github/workflows/container-image.yml` | Builds and pushes `ghcr.io/conductionnl/<app>` for every release, a stable release as its version and `latest`, a beta or unstable release as `edge`. |

The image is for trying an app out and for test environments. Production installs still come from the Nextcloud App Store, and production Kubernetes runs one Nextcloud with many apps rather than a chart per app.

## Rendering

```bash
templates/app-deploy/render.sh <app-id> <path-to-app-repo>
```

The script checks the id against `appinfo/info.xml`, writes the files above and prints a README section for the app. It only overwrites files it wrote before, so running it again brings an app up to the current template. Change the template here, then render it into the apps; do not edit the copies.

## Checking a render

```bash
docker build -t ghcr.io/conductionnl/<app>:test .
docker compose -f docker-compose.yml config -q
helm dependency build charts/<app> && helm lint charts/<app> && helm template t charts/<app>
```

## Choices

- **Nextcloud 33.** The newest image that still ships PHP 8.3; the 34 and 35 images ship PHP 8.5, which not every app supports yet. Every fleet app supports 32 to 34 or later.
- **OpenRegister version.** The newest stable release at build time, never a prerelease, checked against its published SHA-256. Pass `--build-arg OPENREGISTER_VERSION=<version>` to pin it; the baked version and hash are written to `custom_apps/openregister/.image-release`.
- **Root.** Apache starts as root to bind port 80 and serves every request as `www-data`; the entrypoint and the hook run `occ` as `www-data`.
- **Image visibility.** A new GHCR package is private until an organisation owner makes it public.
