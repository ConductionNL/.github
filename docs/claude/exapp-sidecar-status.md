# ExApp Sidecar Wrappers — Status Report

**Date:** 2026-03-05
**Goal:** Get ExApp sidecar wrappers (OpenKlant, OpenZaak, Valtimo, OpenTalk, Keycloak) up and running, following the n8n pattern.

## Summary

All 5 ExApp Docker containers are **running and healthy**. They are **registered with AppAPI** in Nextcloud. However, AppAPI's heartbeat mechanism is not fully completing the initialization cycle for all apps yet.

## What's Done

### Repositories & Submodules
- **keycloak-nextcloud** — New repo created at ConductionNL/keycloak-nextcloud, added as submodule
- **open-webui-nextcloud** — Added as submodule (repo already existed)
- **openklant, openzaak, valtimo, opentalk** — Existing submodules, `ex_app/lib/main.py` rewritten to use `nc_py_api` pattern

### Docker Images Built
| App | Image | Base | Status |
|-----|-------|------|--------|
| Keycloak | `ghcr.io/conductionnl/keycloak-nextcloud:latest` | UBI9-minimal + microdnf Python + Keycloak 26.5.4 | Built, running |
| OpenKlant | `ghcr.io/conductionnl/openklant-exapp:latest` | maykinmedia/open-klant:2.15.0 | Built, running |
| OpenZaak | `ghcr.io/conductionnl/openzaak-exapp:latest` | openzaak/open-zaak:1.27.0 | Built, running |
| Valtimo | `ghcr.io/conductionnl/valtimo-exapp:latest` | eclipse-temurin:17-jre-jammy + ritense/valtimo-backend:12.0.0 | Built, running |
| OpenTalk | `ghcr.io/conductionnl/opentalk-exapp:latest` | python:3.11-slim + opentalk controller v0.31.0-3 | Built, running |

### Docker Compose (openregister/docker-compose.yml)
- All 5 ExApp services added under `commonground` + `exapps` profiles
- Shared infrastructure: `exapp-redis` (Redis 7), `exapp-livekit` (LiveKit WebRTC)
- PostgreSQL databases created: keycloak, openklant, openzaak, opentalk, valtimo
- AppAPI-generated secrets hardcoded in compose for each ExApp
- Healthchecks use Python urllib (no wget/curl dependency)

### AppAPI Registration
- 5 manual-install daemons registered (one per ExApp)
- All 5 apps registered in `oc_ex_apps` table
- Keycloak: **enabled**, OpenKlant/OpenZaak/Valtimo/OpenTalk: **disabled** (pending init)

### Port Assignments (assigned by AppAPI)
| App | Port |
|-----|------|
| n8n | 23000 |
| Keycloak | 23002 |
| OpenZaak | 23003 |
| Valtimo | 23004 |
| OpenKlant | 23005 |
| OpenTalk | 23005 |

## Current Container Status

All 8 ExApp containers running and healthy:
```
openregister-exapp-keycloak    healthy
openregister-exapp-openklant   healthy
openregister-exapp-openzaak    healthy
openregister-exapp-valtimo     healthy
openregister-exapp-opentalk    healthy
openregister-exapp-livekit     healthy
openregister-exapp-redis       healthy
openregister-exapp-n8n         healthy
```

## What's Left / Known Issues

### 1. AppAPI Heartbeat → Init Cycle Not Completing
AppAPI checks heartbeat on each ExApp's assigned port. Some ExApps (valtimo, opentalk) are getting heartbeat counts but others (keycloak, openklant, openzaak) are stuck at 0. This may be an AppAPI internal scheduling issue or related to the high failure count from before we fixed the heartbeat endpoints.

**Possible fix:** Unregister and re-register the stuck ExApps, or investigate AppAPI's heartbeat scheduling.

### 2. Internal Services Not Started
The heartbeat endpoints return `{"status":"waiting"}` (HTTP 200) because the wrapped services (Django, Spring Boot, Rust) only start when AppAPI calls `/init` or `/enabled`. This is the chicken-and-egg: heartbeat must succeed → AppAPI calls init → internal service starts → heartbeat returns "ok".

The 200 status fix should resolve this — AppAPI should proceed to call `/init` once it sees successful heartbeats.

### 3. ZaakAfhandelApp Admin Settings Bug
`/settings/admin/app_api` crashes with "Unknown named parameter $app" in `ZaakAfhandelAppAdmin.php:55`. This is unrelated to the ExApp work but blocks the AppAPI admin UI.

### 4. PostGIS Not Available
OpenZaak may need PostGIS extension but the pgvector PostgreSQL image doesn't include it. OpenZaak may need a different approach (PostGIS Docker image or skip geo features).

### 5. Commits Pending
Changes to entrypoint.sh, main.py (heartbeat fix), Dockerfiles, and docker-compose.yml are local only. Need to commit and push to feature branches for each submodule.

## Files Changed

### docker-compose (openregister/)
- `docker-compose.yml` — Added 5 ExApp services, volumes, healthchecks, secrets, port assignments

### keycloak-nextcloud/ (new repo)
- Full ExApp structure: `ex_app/lib/main.py`, `Dockerfile`, `entrypoint.sh`, `appinfo/info.xml`, CI workflows

### openklant/
- `ex_app/lib/main.py` — Rewritten with nc_py_api, heartbeat returns 200
- `Dockerfile` — Updated base image to 2.15.0
- `entrypoint.sh` — Fixed to use `python3 ex_app/lib/main.py`

### openzaak/
- `ex_app/lib/main.py` — Rewritten with nc_py_api, heartbeat returns 200
- `Dockerfile` — Updated base image to 1.27.0
- `entrypoint.sh` — Fixed to use `python3 ex_app/lib/main.py`
- `appinfo/info.xml` — Fixed registry to ghcr.io

### valtimo/
- `ex_app/lib/main.py` — Rewritten with nc_py_api, heartbeat returns 200
- `Dockerfile` — Rewritten with proper Python install
- `entrypoint.sh` — Fixed to use `python3 ex_app/lib/main.py`
- `appinfo/info.xml` — Fixed registry to ghcr.io

### opentalk/
- `ex_app/lib/main.py` — Rewritten with nc_py_api, heartbeat returns 200
- `Dockerfile` — Added controller.toml config file
- `controller.toml` — New minimal config for OpenTalk controller
- `entrypoint.sh` — Fixed to use `python3 ex_app/lib/main.py`
- `appinfo/info.xml` — Fixed registry to ghcr.io

## Key Learnings

1. **Keycloak UBI9-micro has no package manager** — use UBI9-minimal with microdnf instead
2. **glibc compatibility matters** — Python from Debian/Ubuntu cannot run on UBI9 (glibc 2.38 vs 2.34)
3. **AppAPI assigns unique ports** per ExApp — containers must listen on the assigned port, not hardcoded 23000
4. **APP_SECRET must match** between docker-compose env and AppAPI's database — get secrets from `oc_ex_apps` table
5. **Healthcheck must return 200** even when internal service isn't running, or AppAPI won't proceed to `/init`
6. **Docker compose `${VAR}` in healthcheck** resolves at compose level, not container level — use Python `os.environ` or `$$VAR` instead

## Next Steps

1. Investigate why some ExApps aren't getting heartbeat checks from AppAPI
2. Once heartbeats work, verify `/init` is called and internal services start
3. Enable all 4 disabled ExApps
4. Test through browser at http://localhost:8080
5. Commit all changes to feature branches
6. Push Docker images to ghcr.io
