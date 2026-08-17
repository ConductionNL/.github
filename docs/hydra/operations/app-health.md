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

## Nextcloud apps

| App | main | beta | development |
| --- | --- | --- | --- |
| [decidesk](https://github.com/ConductionNL/decidesk) | ![main](https://github.com/ConductionNL/decidesk/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/decidesk/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/decidesk/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [docudesk](https://github.com/ConductionNL/docudesk) | ![main](https://github.com/ConductionNL/docudesk/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/docudesk/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/docudesk/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [doriath](https://github.com/ConductionNL/doriath) | ![main](https://github.com/ConductionNL/doriath/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/doriath/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/doriath/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [hermiq](https://github.com/ConductionNL/hermiq) | ![main](https://github.com/ConductionNL/hermiq/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/hermiq/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/hermiq/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [larpingapp](https://github.com/ConductionNL/larpingapp) | ![main](https://github.com/ConductionNL/larpingapp/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/larpingapp/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/larpingapp/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [launchpad](https://github.com/ConductionNL/launchpad) | ![main](https://github.com/ConductionNL/launchpad/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/launchpad/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/launchpad/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [nldesign](https://github.com/ConductionNL/nldesign) | ![main](https://github.com/ConductionNL/nldesign/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/nldesign/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/nldesign/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [openbuild](https://github.com/ConductionNL/openbuild) | ![main](https://github.com/ConductionNL/openbuild/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/openbuild/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/openbuild/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [opencatalogi](https://github.com/ConductionNL/opencatalogi) | ![main](https://github.com/ConductionNL/opencatalogi/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/opencatalogi/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/opencatalogi/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [openconnector](https://github.com/ConductionNL/openconnector) | ![main](https://github.com/ConductionNL/openconnector/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/openconnector/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/openconnector/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [openregister](https://github.com/ConductionNL/openregister) | ![main](https://github.com/ConductionNL/openregister/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/openregister/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/openregister/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [pipelinq](https://github.com/ConductionNL/pipelinq) | ![main](https://github.com/ConductionNL/pipelinq/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/pipelinq/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/pipelinq/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [planix](https://github.com/ConductionNL/planix) | ![main](https://github.com/ConductionNL/planix/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/planix/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/planix/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [portaliq](https://github.com/ConductionNL/portaliq) | ![main](https://github.com/ConductionNL/portaliq/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/portaliq/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/portaliq/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [procest](https://github.com/ConductionNL/procest) | ![main](https://github.com/ConductionNL/procest/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/procest/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/procest/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [scholiq](https://github.com/ConductionNL/scholiq) | ![main](https://github.com/ConductionNL/scholiq/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/scholiq/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/scholiq/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [shillinq](https://github.com/ConductionNL/shillinq) | ![main](https://github.com/ConductionNL/shillinq/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/shillinq/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/shillinq/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [softwarecatalog](https://github.com/ConductionNL/softwarecatalog) | ![main](https://github.com/ConductionNL/softwarecatalog/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/softwarecatalog/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/softwarecatalog/actions/workflows/code-quality.yml/badge.svg?branch=development) |
| [zaakafhandelapp](https://github.com/ConductionNL/zaakafhandelapp) | ![main](https://github.com/ConductionNL/zaakafhandelapp/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/zaakafhandelapp/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/zaakafhandelapp/actions/workflows/code-quality.yml/badge.svg?branch=development) |

## Libraries

Not Nextcloud apps — they carry no `appinfo/info.xml` — but every app depends on
them, so a regression here reaches the whole fleet.

| Library | main | beta | development |
| --- | --- | --- | --- |
| [nextcloud-vue](https://github.com/ConductionNL/nextcloud-vue) | ![main](https://github.com/ConductionNL/nextcloud-vue/actions/workflows/code-quality.yml/badge.svg?branch=main) | ![beta](https://github.com/ConductionNL/nextcloud-vue/actions/workflows/code-quality.yml/badge.svg?branch=beta) | ![development](https://github.com/ConductionNL/nextcloud-vue/actions/workflows/code-quality.yml/badge.svg?branch=development) |

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
app running `Code Quality` that the working fleet list did not include.

Archived repositories are excluded.
