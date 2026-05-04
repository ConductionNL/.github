# Docker Environment

Uses `openregister/docker-compose.yml`. Default starts db + nextcloud + n8n.

## Reset

```bash
bash clean-env.sh
```
Or use the `/clean-env` skill.

## Available Profiles

Add one or more profiles with `--profile <name>`:

| Profile | What it adds |
|---------|-------------|
| `ai` | AI/LLM services |
| `ui` | Separate frontend UI container |
| `exapps` | ExApp sidecar containers |
| `solr` | Solr search |
| `elasticsearch` | Elasticsearch |
| `ollama` | Local LLM via Ollama |
| `standalone` | Standalone mode (no Nextcloud) |
| `mariadb` | MariaDB instead of default DB |
| `openproject` | OpenProject |
| `xwiki` | XWiki |
| `ox` | Open-Xchange |
| `valtimo` | Valtimo BPM |
| `openzaak` | OpenZaak |
| `openklant` | OpenKlant |

**Example:**
```bash
docker compose --profile ui --profile exapps up -d
```

For MCP browser pool configuration (Playwright sessions used by testing commands), see [playwright-setup.md](playwright-setup.md).
