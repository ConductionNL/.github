# Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Not logged in · Please run /login` | `--bare` flag or missing credentials | Ensure entrypoint uses `--output-format stream-json`, not `--bare` |
| `OAuth token has expired` | Static `CLAUDE_CODE_OAUTH_TOKEN` in `.env` | Use credentials.json instead (auto-refresh), or run `claude setup-token` |
| `GIT_TOKEN does not have push access` | PAT lacks `contents:write` or no repo access | Regenerate PAT with correct scopes, verify repo collaborator access |
| `Failed to connect to github.com port 443` | Egress blocked (iptables in rootless) | Remove `--cap-add NET_ADMIN` from run flags (done in current dev-run.sh) |
| `EROFS: read-only file system` on `/spec/` | Spec mount is `:ro` by design | Expected — spec updates must happen outside the container |
| Container exits immediately | Missing required env var | Check entrypoint output for `is required` error messages |
| `Bind for 0.0.0.0:808x failed: port is already allocated` | Orphaned NC container from a crashed pipeline | `docker ps -a --filter "name=hydra-nc" \| xargs docker rm -f`. The orchestrator now auto-cleans on startup (since v0.1.1). |
| Browser tests fail with `Nextcloud not reachable` | NC server didn't start or port conflict | Check `browser-nc-setup.log` for errors. Verify port with `ss -tlnp \| grep 808`. |

---

## Cleanup

### Temp directories

Pipeline runs create temp dirs in `/tmp/hydra-*`. These are **not** automatically cleaned
on crash. To clean up:

```bash
# Safe cleanup — keeps NC cache (saves ~1 min per quality run)
for d in /tmp/hydra-*; do
    case "$d" in
        /tmp/hydra-nc-cache|/tmp/hydra-slots) echo "KEEP: $d" ;;
        *) rm -rf "$d" && echo "REMOVED: $d" ;;
    esac
done

# Some quality dirs are Docker-owned (root) — use Docker to remove
docker run --rm -v /tmp:/tmp alpine sh -c "rm -rf /tmp/hydra-quality-*"
```

### NC cache (`/tmp/hydra-nc-cache`)

The NC cache stores a pre-downloaded Nextcloud server (~964 MB). `run-quality.sh` checks
for it before downloading. **Keep this directory** — without it, every quality run downloads
Nextcloud from scratch, adding ~60 seconds per pipeline.

The cache is safe to delete if disk space is needed:
```bash
rm -rf /tmp/hydra-nc-cache
```

### Stale slot locks

If a pipeline crashes, its slot lock (`/tmp/hydra-slots/slot-N.lock`) may persist.
`cron-hydra.sh` auto-detects stale locks (checks if the PID is alive), but you can
manually clear them:

```bash
rm -f /tmp/hydra-slots/slot-*.lock
```

### Orphaned containers

List and remove orphaned Hydra containers:

```bash
docker ps -a --filter "name=hydra-nc" --format "{{.ID}} {{.Names}} {{.Status}}"
docker rm -f $(docker ps -aq --filter "name=hydra-nc")
```
