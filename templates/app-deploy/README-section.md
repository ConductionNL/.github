### Try it with Docker

The repository builds an evaluation image: the official Nextcloud image with __APP_ID__ and OpenRegister installed and enabled. It is meant for trying the app out and for test environments. For production, install the app from the Nextcloud App Store.

```bash
docker compose -f __COMPOSE_FILE__ up -d --build
```

Open http://localhost:8080/apps/__APP_ID__/ and sign in as `admin` with password `admin`. The first start takes a minute or two. Set `NEXTCLOUD_ADMIN_PASSWORD` and `APP_PORT` to change the password and the port; `__COMPOSE_FILE__` lists every setting. `docker compose -f __COMPOSE_FILE__ down -v` removes the stack and its data.

Released versions are published as `ghcr.io/conductionnl/__APP_ID__`, so leaving out `--build` uses the published image.

### Run it on Kubernetes

`charts/__APP_ID__` wraps the official [Nextcloud Helm chart](https://github.com/nextcloud/helm) and runs the same image with PostgreSQL:

```bash
helm dependency build charts/__APP_ID__
helm install __APP_ID__ charts/__APP_ID__ --set nextcloud.nextcloud.host=__APP_ID__.example.org
```

Change the passwords in `charts/__APP_ID__/values.yaml` before you install it anywhere that matters.
