# Conduction Development Environment

Shared Docker Compose setup for all ConductionNL Nextcloud app development. The compose file lives in this repository (`.github/docker-compose.yml`) and is used by all Conduction apps.

## Prerequisites

- Docker and Docker Compose v2+
- The workspace directory should contain all app repos as siblings of `.github/`:
  ```
  apps-extra/
  ├── .github/              ← this repo (contains docker-compose.yml)
  ├── openregister/
  ├── opencatalogi/
  ├── softwarecatalog/
  ├── nldesign/
  ├── mydash/
  ├── docudesk/
  ├── procest/
  ├── pipelinq/
  ├── zaakafhandelapp/
  ├── larpingapp/
  └── ...
  ```

## Quick Start

```bash
# Start the core environment (db + nextcloud + n8n)
docker compose -f .github/docker-compose.yml up -d

# Nextcloud is available at http://localhost:8080
# Login: admin / admin
```

## Profiles

The compose file uses Docker profiles to organize optional services. Only the core services (db, nextcloud, exapp-n8n) start by default.

### Starting with profiles

```bash
# Single profile
docker compose -f .github/docker-compose.yml --profile mail up -d

# Multiple profiles
docker compose -f .github/docker-compose.yml --profile mail --profile ai up -d

# Everything (not recommended — very resource heavy)
docker compose -f .github/docker-compose.yml --profile mail --profile ai --profile commonground --profile integrations up -d
```

### Available profiles

| Profile | Services | Purpose | Resources |
|---------|----------|---------|-----------|
| *(default)* | db, nextcloud, exapp-n8n | Core dev environment | ~1 GB |
| `demo` | nextcloud-demo | Self-contained demo (installs from app store) | ~1 GB |
| `mail` | greenmail | Test mail server (SMTP/IMAP) | ~512 MB |
| `ai` | presidio, tgi-llm, dolphin-vlm, openanonymiser, exapp-openwebui | AI/LLM services | ~40 GB + GPU |
| `ollama` | ollama | Standalone LLM inference | ~16 GB + GPU |
| `ui` | tilburg-woo-ui | Public WOO document frontend | ~256 MB |
| `exapps` | harp, redis, livekit, minio | AppAPI infrastructure | ~1 GB |
| `commonground` | keycloak, redis, livekit, minio, exapp-openklant, exapp-openzaak, exapp-valtimo, exapp-opentalk | Common Ground ExApps | ~10 GB |
| `solr` / `search` | solr, zookeeper | Solr search engine | ~1 GB |
| `elasticsearch` | elasticsearch | Elasticsearch backend | ~1 GB |
| `standalone` | n8n, open-webui | Standalone versions (not ExApps) | ~1 GB |
| `llm-management` | openllm | LLM model management | ~16 GB + GPU |
| `mariadb` | db-mariadb, nextcloud-mariadb | MariaDB compatibility testing | ~1 GB |
| `openproject` / `integrations` | openproject | Project management | ~4 GB |
| `xwiki` / `integrations` | xwiki | Wiki platform | ~4 GB |
| `ox` / `integrations` | open-xchange | Email and groupware (requires registry access) | ~4 GB |
| `valtimo` / `commonground` | valtimo | BPM and case management | ~2 GB |
| `openzaak` / `commonground` | openzaak | ZGW API case management | ~2 GB |
| `openklant` / `commonground` | openklant | Customer interaction registry | ~1 GB |
| `exapps-legacy` | docker-socket-proxy | Legacy AppAPI deploy daemon | ~128 MB |

## Service Details

### Core: Nextcloud + PostgreSQL

| Service | Container | Port | Notes |
|---------|-----------|------|-------|
| PostgreSQL | `conduction-postgres` | 5432 | pgvector enabled, shared by all services |
| Nextcloud | `nextcloud` | 8080 | Admin: `admin` / `admin` |
| n8n ExApp | `conduction-exapp-n8n` | — | Via Nextcloud AppAPI proxy |

All Conduction apps are mounted as volumes into Nextcloud's `custom_apps` directory. Changes to app source code are immediately reflected.

### Mail & Groupware

Two options are available depending on your needs:

| | GreenMail (`--profile mail`) | Open-Xchange (`--profile ox`) |
|---|---|---|
| **Use for** | Day-to-day development, quick testing | Production-like integration, client demos |
| **Complexity** | Zero config, works immediately | Multi-service, requires registry access |
| **Mail** | SMTP + IMAP (auto-create accounts) | Full IMAP/SMTP via Dovecot/Postfix |
| **Calendar** | Use Nextcloud Calendar (CalDAV) | Built-in calendar + CalDAV |
| **Contacts** | Use Nextcloud Contacts (CardDAV) | Built-in contacts + CardDAV |
| **Web UI** | REST API at :8085 | Full webmail at :8087 |
| **Seed data** | Scripts included | CLI user/context creation |

#### Option A: GreenMail (recommended for development)

Lightweight test mail server. Accounts auto-created on first email. No configuration needed.

| Service | Container | Port | Protocol |
|---------|-----------|------|----------|
| GreenMail | `conduction-greenmail` | 3025 | SMTP |
| | | 3143 | IMAP |
| | | 3110 | POP3 |
| | | 8085 | Web UI / REST API |

**Setup:**

```bash
# 1. Start
docker compose -f .github/docker-compose.yml --profile mail up -d

# 2. Seed test emails (creates accounts automatically)
bash .github/docker/mail/seed-mail.sh

# 3. Seed contacts and calendar events into Nextcloud
bash .github/docker/mail/seed-pim.sh
```

**Configure Nextcloud Mail app:**
- Go to Nextcloud (http://localhost:8080) → Mail app → Settings
- Add account:
  - **IMAP**: Host `greenmail`, Port `3143`, Security `None`
  - **SMTP**: Host `greenmail`, Port `3025`, Security `None`
  - **User**: `behandelaar@test.local` (or any seeded address)
  - **Password**: same as the email address

**Test accounts** (auto-created by seed script):

| Email | Role | Description |
|-------|------|-------------|
| `admin@test.local` | System admin | Administrative notifications |
| `behandelaar@test.local` | Case handler | Processes applications and cases |
| `coordinator@test.local` | Team coordinator | Planning, oversight, IT liaison |
| `burger@test.local` | Citizen | Submits applications and complaints |
| `leverancier@test.local` | Supplier/vendor | External IT partner |

**Seed data includes:**
- 12 emails: case applications, status updates, internal coordination, complaints, deadlines
- 6 contacts: citizens, civil servants, VNG architect, supplier (CardDAV)
- 5 calendar events: sprint review, welstandscommissie, IT overleg, deadlines, retrospective (CalDAV)

All seed data is interconnected around realistic Dutch municipal case management scenarios (omgevingsvergunning, kapvergunning, IT-migratie).

#### Option B: Open-Xchange (for production-like testing)

Full groupware suite with integrated webmail, calendar, contacts, and document editing (OX Text + Spreadsheet). Uses GreenMail as its IMAP/SMTP backend — the same mail server, so both OX and Nextcloud Mail see the same emails.

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| Open-Xchange | `conduction-open-xchange` | 8087 | Web UI (AppSuite) |
| OX MariaDB | `conduction-ox-mariadb` | — | Dedicated database for OX |
| GreenMail | `conduction-greenmail` | 3025/3143/8085 | Shared IMAP/SMTP (auto-starts) |

**Architecture:**
```
GreenMail (IMAP/SMTP)
├── OX AppSuite → authenticates + reads/sends mail via IMAP/SMTP
└── Nextcloud Mail → reads/sends mail via IMAP/SMTP
    Both see the same mailboxes and emails.
```

**Setup:**

```bash
# 1. Start OX (also starts GreenMail + OX MariaDB automatically)
docker compose -f .github/docker-compose.yml --profile ox up -d

# 2. Wait for OX to finish initialization (first boot takes 2-3 minutes)
docker logs -f conduction-open-xchange
# Wait for: "*** Restart completed ***"

# 3. Seed test emails into GreenMail
bash .github/docker/mail/seed-mail.sh

# 4. Create OX users and seed contacts/calendar
bash .github/docker/mail/seed-ox.sh

# 5. Access OX at http://localhost:8087/appsuite
```

**Login credentials:**

| Username | Password | Role |
|----------|----------|------|
| `oxadmin` | `oxadmin` | Context admin |
| `behandelaar` | `behandelaar@test.local` | Case handler |
| `coordinator` | `coordinator@test.local` | Team coordinator |
| `burger` | `burger@test.local` | Citizen |
| `leverancier` | `leverancier@test.local` | Supplier |

Note: User passwords match their GreenMail email addresses because OX authenticates via IMAP against GreenMail.

**What's included after seeding:**
- 5 user accounts with Dutch names and roles
- 4 contacts (citizens, supplier, VNG architect)
- 2 calendar appointments (welstandscommissie, IT-overleg)
- 12 emails visible in OX webmail (from seed-mail.sh via GreenMail)
- OX Text and Spreadsheet editors enabled

**Connecting Nextcloud to OX:**
- Both OX and Nextcloud Mail share the same GreenMail IMAP server
- Configure Nextcloud Mail with: IMAP host `greenmail`, port `3143` (same as standalone mail profile)
- OX can mount Nextcloud files via WebDAV for document collaboration

**Resource requirements:**
- OX needs ~2-4 GB RAM
- First boot initializes databases and takes 2-3 minutes
- Subsequent boots are faster (config is persisted in `ox-etc` volume)

### AI Services (--profile ai)

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| Presidio | `conduction-presidio-analyzer` | 5001 | PII detection (Microsoft) |
| TGI LLM | `conduction-tgi-llm` | 8081 | Text generation (HuggingFace) |
| Dolphin VLM | `conduction-dolphin-vlm` | 8083 | Document parsing (Vision LM) |
| OpenAnonymiser | `conduction-openanonymiser` | 5002 | PII anonymisation |
| OpenWebUI ExApp | `conduction-exapp-openwebui` | — | AI chat via Nextcloud |

Requires NVIDIA GPU with Docker GPU support configured.

### Common Ground (--profile commonground)

Dutch government Common Ground services, running as Nextcloud ExApps:

| Service | Container | Port | Purpose |
|---------|-----------|------|---------|
| Keycloak | `conduction-exapp-keycloak` | 8180 | Identity management (OIDC) |
| OpenKlant ExApp | `conduction-exapp-openklant` | — | Customer interaction registry |
| OpenZaak ExApp | `conduction-exapp-openzaak` | — | ZGW case management |
| Valtimo ExApp | `conduction-exapp-valtimo` | — | BPM and case management |
| OpenTalk ExApp | `conduction-exapp-opentalk` | — | Video conferencing |
| Redis | `conduction-exapp-redis` | — | Shared cache |
| LiveKit | `conduction-exapp-livekit` | 7880 | WebRTC media server |
| MinIO | `conduction-exapp-minio` | — | Object storage |

## Common Operations

### Reset the environment

```bash
# Stop everything and remove volumes (full reset)
docker compose -f .github/docker-compose.yml down -v

# Restart
docker compose -f .github/docker-compose.yml up -d
```

### Install apps after reset

```bash
docker exec nextcloud php occ app:enable openregister
docker exec nextcloud php occ app:enable opencatalogi
docker exec nextcloud php occ app:enable softwarecatalog
docker exec nextcloud php occ app:enable nldesign
docker exec nextcloud php occ app:enable mydash
```

### Clear caches

```bash
# OPcache (after PHP changes)
docker exec nextcloud apache2ctl graceful

# APCu
docker exec nextcloud php -r "apcu_clear_cache();"

# Brute force protection
docker exec nextcloud php occ security:bruteforce:reset 127.0.0.1
```

### Fix file permissions

```bash
docker exec -u root nextcloud chown -R www-data:www-data /var/www/html/custom_apps/
```

### View logs

```bash
# Nextcloud log
docker exec nextcloud tail -f /var/www/html/data/nextcloud.log

# Specific container
docker logs -f conduction-postgres
```

## Port Map

Quick reference for all service ports:

| Port | Service | Profile |
|------|---------|---------|
| 2181 | ZooKeeper | solr |
| 2375 | Docker Socket Proxy | exapps-legacy |
| 3025 | GreenMail SMTP | mail |
| 3110 | GreenMail POP3 | mail |
| 3143 | GreenMail IMAP | mail |
| 3306 | MariaDB | mariadb |
| 5001 | Presidio Analyzer | ai |
| 5002 | OpenAnonymiser | ai |
| 5432 | PostgreSQL | *(default)* |
| 5678 | n8n (standalone) | standalone |
| 7880 | LiveKit | commonground |
| 8080 | **Nextcloud** | *(default)* |
| 8081 | TGI LLM | ai |
| 8083 | Dolphin VLM | ai |
| 8085 | GreenMail Web UI | mail |
| 8086 | OpenProject | openproject |
| 8087 | Open-Xchange | ox |
| 8088 | XWiki | xwiki |
| 8089 | Valtimo | valtimo |
| 8090 | OpenZaak | openzaak |
| 8091 | OpenKlant | openklant |
| 8180 | Keycloak | commonground |
| 8780 | HaRP | exapps |
| 8983 | Solr | solr |
| 9200 | Elasticsearch | elasticsearch |
| 11434 | Ollama | ollama |

## Demo Mode (--profile demo)

Self-contained demo environment that installs apps from the Nextcloud app store. No source code needed — just start and demo.

```bash
docker compose -f .github/docker-compose.yml --profile demo up -d
```

This starts a Nextcloud instance that automatically installs OpenRegister, OpenCatalogi, and SoftwareCatalog from the app store. Useful for demos, stakeholder reviews, and quick testing without a full development setup.

**Note**: The `demo` profile uses a different Nextcloud service than the default. Do not combine `demo` with the default profile.

## Database Testing (--profile mariadb)

The MariaDB profile provides compatibility testing against MariaDB instead of PostgreSQL.

```bash
# Start with MariaDB
docker compose -f .github/docker-compose.yml --profile mariadb up -d
```

An automated test script is available for running integration tests against both databases:
```bash
bash .github/docker/test-database-compatibility.sh
```

Key differences between PostgreSQL and MariaDB:
- **Vector search**: Only available with PostgreSQL (pgvector)
- **Full-text search**: Both supported, different syntax
- **JSON operations**: PostgreSQL has richer JSON support
- **Boolean handling**: MariaDB uses 0/1, PostgreSQL uses true/false

See [docker/README-DATABASE-TESTING.md](../docker/README-DATABASE-TESTING.md) for detailed documentation.

## Migrating from OpenRegister docker-compose

If you were previously using `openregister/docker-compose.yml`, update your commands:

```bash
# Old
docker compose -f openregister/docker-compose.yml up -d

# New
docker compose -f .github/docker-compose.yml up -d
```

Container names have changed from `openregister-*` to `conduction-*` (except `nextcloud` which stays the same). The network is now `conduction-network` instead of `openregister-network`.

**Note**: You may need to remove old volumes if switching:
```bash
docker compose -f openregister/docker-compose.yml down -v
docker compose -f .github/docker-compose.yml up -d
```
