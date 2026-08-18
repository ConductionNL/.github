# App health

Live `Code Quality` status for every Conduction Nextcloud app, on each of the
three branches it ships through. Badges come straight from GitHub Actions and
update themselves — click one to open that branch's runs.

:::caution Read a badge carefully — red is not one thing

A **grey `no status`** badge does not mean healthy. It means the workflow has
**never run on that branch**. Unmeasured and passing look identical here, and
unmeasured is the more expensive of the two.

A **red** badge has at least five distinct causes, and only the first is what
most readers assume:

1. A check genuinely failed.
2. The workflow never started (`startup_failure`) — nothing was ever measured.
3. `gate-4 composer-audit` hit an advisory that has since been **withdrawn**.
   It reads a live feed, so a rerun clears it with no code change.
4. A GitHub platform incident (`codeload` 429/503) meant the job could not
   download its own dependencies.
5. The job **ran, exited non-zero, and did no work** — which renders exactly
   like a real failure.

The ten-second discriminator for 3–5 is the log: open the run and check the job
produced its own output marker (`Tests:`, `[gate-`, `assertions`). A PHP job log
of ~3 KB did nothing.
:::

:::tip These badges show the BRANCH, not the last pull request

Each badge is filtered to **`event=push`**, so it reflects the state of the
branch itself — the run that fired when a commit landed on it.

That filter is load-bearing. GitHub's own badge endpoint
(`github.com/.../badge.svg?branch=X`) has **no event parameter**: it renders the
newest run on the branch *whatever the event*, and a pull request whose **head**
is `development` counts as "on development". The fleet promotes with
`development -> beta` pull requests, so those promotion runs landed under the
`development` badge and, being newer, won.

Measured 2026-08-18 — six apps, all with a green `development` branch:

| App | branch (push) | GitHub badge | shields badge (`event=push`) |
| --- | --- | --- | --- |
| hermiq | success | **failing** | passing |
| openconnector | success | **failing** | passing |
| pipelinq | success | **failing** | passing |
| shillinq | success | **failing** | passing |
| opencatalogi | success | passing | passing |
| openregister | success | passing | passing |

Four apps read as broken while their branches were green. A red badge here now
means the branch is red — a failing promotion pull request no longer shows up as
one.

To check a branch yourself:

```
gh api "repos/ConductionNL/<app>/actions/workflows/code-quality.yml/runs?branch=development&event=push&per_page=5" \
  --jq '[.workflow_runs[]]|sort_by(.created_at)|reverse|.[0]|"\(.conclusion) \(.created_at)"'
```

⚠️ Two things these badges still cannot tell you. **shields.io caches** for a
few minutes, so a badge can lag a run that has just finished — when it matters,
read the API. And a **grey `no status`** badge still means the workflow has
never run on that branch with that event: unmeasured, not healthy.
:::

## Nextcloud apps

| App | main | beta | development |
| --- | --- | --- | --- |
| [decidesk](https://github.com/ConductionNL/decidesk) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/decidesk/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/decidesk/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/decidesk/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/decidesk/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/decidesk/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/decidesk/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [docudesk](https://github.com/ConductionNL/docudesk) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/docudesk/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/docudesk/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/docudesk/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/docudesk/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/docudesk/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/docudesk/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [doriath](https://github.com/ConductionNL/doriath) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/doriath/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/doriath/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/doriath/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/doriath/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/doriath/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/doriath/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [hermiq](https://github.com/ConductionNL/hermiq) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/hermiq/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/hermiq/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/hermiq/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/hermiq/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/hermiq/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/hermiq/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [larpingapp](https://github.com/ConductionNL/larpingapp) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/larpingapp/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/larpingapp/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/larpingapp/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/larpingapp/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/larpingapp/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/larpingapp/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [launchpad](https://github.com/ConductionNL/launchpad) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/launchpad/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/launchpad/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/launchpad/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/launchpad/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/launchpad/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/launchpad/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [nldesign](https://github.com/ConductionNL/nldesign) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/nldesign/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/nldesign/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/nldesign/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/nldesign/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/nldesign/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/nldesign/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [openbuild](https://github.com/ConductionNL/openbuild) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/openbuild/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/openbuild/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/openbuild/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/openbuild/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/openbuild/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/openbuild/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [opencatalogi](https://github.com/ConductionNL/opencatalogi) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/opencatalogi/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/opencatalogi/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/opencatalogi/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/opencatalogi/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/opencatalogi/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/opencatalogi/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [openconnector](https://github.com/ConductionNL/openconnector) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/openconnector/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/openconnector/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/openconnector/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/openconnector/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/openconnector/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/openconnector/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [openregister](https://github.com/ConductionNL/openregister) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/openregister/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/openregister/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/openregister/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/openregister/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/openregister/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/openregister/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [pipelinq](https://github.com/ConductionNL/pipelinq) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/pipelinq/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/pipelinq/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/pipelinq/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/pipelinq/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/pipelinq/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/pipelinq/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [portaliq](https://github.com/ConductionNL/portaliq) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/portaliq/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/portaliq/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/portaliq/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/portaliq/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/portaliq/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/portaliq/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [procest](https://github.com/ConductionNL/procest) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/procest/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/procest/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/procest/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/procest/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/procest/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/procest/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [scholiq](https://github.com/ConductionNL/scholiq) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/scholiq/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/scholiq/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/scholiq/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/scholiq/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/scholiq/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/scholiq/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [shillinq](https://github.com/ConductionNL/shillinq) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/shillinq/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/shillinq/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/shillinq/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/shillinq/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/shillinq/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/shillinq/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |
| [softwarecatalog](https://github.com/ConductionNL/softwarecatalog) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/softwarecatalog/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/softwarecatalog/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/softwarecatalog/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/softwarecatalog/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/softwarecatalog/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/softwarecatalog/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |

## Deprecated apps

Still in the repository and still building, but **not being taken forward**.
They are listed because a deprecated app that disappears from the dashboard
becomes an app nobody is measuring — and unmeasured is the state this page
exists to make visible. Red here is informational: do not spend effort greening
a row in this table without checking first whether the work is wanted.

| App | main | beta | development | Status |
| --- | --- | --- | --- | --- |
| [planix](https://github.com/ConductionNL/planix) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/planix/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/planix/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/planix/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/planix/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/planix/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/planix/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) | deprecated |
| [zaakafhandelapp](https://github.com/ConductionNL/zaakafhandelapp) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/zaakafhandelapp/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/zaakafhandelapp/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/zaakafhandelapp/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/zaakafhandelapp/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/zaakafhandelapp/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/zaakafhandelapp/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) | deprecated |

## Renaming

Apps are being renamed onto a common suffix. Both names appear in the wild
during a rename — the repository, the `appinfo/info.xml` id, the OpenSpec
directory and the App Store listing do not all move on the same day — so this
table is the mapping of record.

⚠️ **A rename is a data migration, not a find-and-replace.** The app id appears
in `appinfo/info.xml`, route names, OpenRegister register slugs, app-config
keys, and any object already written under the old id. Renaming the repository
alone leaves live data pointing at a name nothing answers to.

| Old name | New name | Status |
| --- | --- | --- |
| `mydash` | **`launchpad`** | done — the `mydash` repo is archived; treat any surviving reference as stale |
| `scholiq` | `Learniq` | planned |
| `nldesign` | `Themiq` | planned |
| `hrmq` | `Humaniq` | planned |
| `decidesk` | `Decidiq` | planned |
| `larpingapp` | `Larpiq` | planned |
| `openbuild` | `Buildiq` | planned |

Until a row reads *done*, the **old** name is the one that resolves — the badges
above and every `gh` command still use it.

## Libraries

Not Nextcloud apps — they carry no `appinfo/info.xml` — but every app depends on
them, so a regression here reaches the whole fleet.

| Library | main | beta | development |
| --- | --- | --- | --- |
| [nextcloud-vue](https://github.com/ConductionNL/nextcloud-vue) | [![main](https://img.shields.io/github/actions/workflow/status/ConductionNL/nextcloud-vue/code-quality.yml?branch=main&event=push&label=main)](https://github.com/ConductionNL/nextcloud-vue/actions/workflows/code-quality.yml?query=branch%3Amain+event%3Apush) | [![beta](https://img.shields.io/github/actions/workflow/status/ConductionNL/nextcloud-vue/code-quality.yml?branch=beta&event=push&label=beta)](https://github.com/ConductionNL/nextcloud-vue/actions/workflows/code-quality.yml?query=branch%3Abeta+event%3Apush) | [![development](https://img.shields.io/github/actions/workflow/status/ConductionNL/nextcloud-vue/code-quality.yml?branch=development&event=push&label=development)](https://github.com/ConductionNL/nextcloud-vue/actions/workflows/code-quality.yml?query=branch%3Adevelopment+event%3Apush) |

## Not on this page, and why

**`hrmq`** is a Nextcloud app but ships **no `Code Quality` workflow**, so there
is nothing to badge. That absence is worth more attention than any red cell
here: an app with no quality workflow cannot fail one.

**`openanonymiser`** is not a Nextcloud app (no `appinfo/info.xml`) and runs no
`Code Quality` workflow.

**`nextcloud-app-template`** and **`app-versions`** carry `appinfo/info.xml` but
are scaffold and tooling rather than products. Both run `Code Quality`. The
template being red matters, because every newly generated app inherits its
starting state.

## How this list is built

Membership comes from two checks, not from a hand-maintained list: the app
appears in the public site's `apps-catalog.js`, **and** the repository carries
`appinfo/info.xml` on its default branch — the canonical marker of a Nextcloud
app.

That matters. A hand-maintained fleet list previously omitted seven live apps,
and one of them carried well over a thousand outstanding gate findings while
going entirely unmeasured, because nothing swept an app that wasn't on the list.
Building this page from the catalog immediately surfaced `planix`, a Nextcloud
app running `Code Quality` that the working fleet list did not include. It is
now listed under **Deprecated apps** — which is the point: it went unmeasured
for months precisely because no list carried it, and "deprecated" is a reason to
record an app, not to drop it.

**This page is the list of record.** If an app is not on it — active,
deprecated, or excluded with a reason below — it is not being measured by
anybody. Add the row before you need it.

Archived repositories are excluded.
