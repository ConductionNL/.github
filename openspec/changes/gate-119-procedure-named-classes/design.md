# Design: gate-119 procedure-named-classes

## What counts

A file counts when all of these hold:

1. Its path is under `lib/` or `src/`.
2. Its extension is `.php`, `.vue`, `.js` or `.ts`.
3. It is not under `lib/Migration/`, `lib/Settings/`, `src/manifest.json` or `src/manifest.d/`. Configuration is where a procedure name belongs.
4. One of its path tokens is in the vocabulary.

Tokens come from every path segment below `lib/` or `src/`, with the extension stripped. Each segment is split on CamelCase, digits, `-` and `_`, lowercased, and the whole lowercased segment is added as well. `WOODeadlineService.php` gives `woo`, `deadline`, `service` and `woodeadlineservice`. `Service/Bezwaar/HearingService.php` counts through its directory.

A file with a procedure token is **procedure**, even when it also has a standard token. A file with only a standard token is **standard**.

## The vocabulary

`hydra-gates/contracts/procedure-vocabulary.json`:

```json
{
  "procedure": ["woo", "wob", "bezwaar", "beroep", "beschikking", "vth", "handhaving", "toezicht",
    "omgevingsvergunning", "vergunning", "vergunningaanvraag", "termijn", "subsidie", "besluit",
    "besluitvorming", "beslistermijn", "leerplicht", "verzuim", "bpv", "verlof", "dwangsom", "lhs",
    "mandaat", "ingebrekestelling", "aanvullingsverzoek", "samenwerkverzoek", "hoorzitting", "wmo",
    "jeugdwet", "participatiewet", "bibob", "cao", "poortwachter", "awb", "sociaaldomein",
    "staatssteun", "terugvordering", "vaststelling", "tussenrapportage", "bewijsstuk",
    "cofinanciering", "uitbetaling", "zaakdossier", "informatieobject", "deelzaak"],
  "standard": ["zgw", "zrc", "ztc", "drc", "brc", "nrc", "stuf", "zkn", "brp", "kvk", "bag", "pdok",
    "haalcentraal", "dso", "digid", "eherkenning", "peppol", "sbr", "xbrl", "diwoo", "tenderned",
    "digipoort", "libresign", "verzuimloket", "iwmo", "ijw"]
}
```

An app may add tokens in its baseline file under `extraProcedureTokens`. It may not remove shared ones.

Domain nouns that are not statutory procedures stay out: `leave` (humaniq), `dunning` and `vat` (shillinq). They are what those apps are for.

## The baseline file

`.hydra/procedure-names.json` in the app repo:

```json
{
  "gate": "procedure-named-classes",
  "adr": "ADR-118",
  "procedure": ["lib/Service/WOODecisionService.php", "..."],
  "standard": ["lib/Service/Stuf/StufHttpClient.php", "..."],
  "extraProcedureTokens": []
}
```

- `procedure` is the allowlist of procedure-named files. It only shrinks.
- `standard` is the standards-adapter allowlist. A standards file outside it is a warning in a leaf app, and passes in integriq.
- `--write-baseline` writes the file from the current tree, sorted. A lane runs it once at adoption. After that a lane only deletes lines.

## The verdict

| Check | Result |
|---|---|
| A procedure-named file at head is not in `procedure` | FAIL, names the file and the token |
| Procedure count at head is above the count at the base ref | FAIL, prints base, head and delta |
| A standards-named file at head is not in `standard`, in a repo other than integriq | WARN, names integriq or filinq as the home |
| A baseline entry no longer exists | INFO, listed under `--shrinkable` |
| No baseline file and no procedure-named file | PASS |
| No baseline file and procedure-named files exist | FAIL, says to run `--write-baseline` |
| No `lib/` and no `src/` | NOT APPLICABLE |

The base-ref count makes a stale baseline harmless. A deleted file that stays in the baseline cannot come back, because the count would rise.

## Exceptions

A docblock or leading comment `@procedure-name exclude <reason>` removes a file from the head count. The reason is graded by the shared `exclusion_reason.is_reason_bearing()`. A bare marker does not count. Expected uses: a deprecated shim that forwards to a generic class for one release.

## Scope

The count is app-wide, as the custom-widget ratchet does. A scoped run still counts the whole tree, because a rename in one file changes the total. Only the new-file check is diff-scoped: it looks at files added or renamed against `HYDRA_GATE_BASE_REF`.

## Adoption numbers

Measured on `origin/development`, 10 October 2026, with the vocabulary above:

| App | Procedure | Standard |
|---|---:|---:|
| dossiq | 229 | 109 |
| humaniq | 8 | 1 |
| shillinq | 8 | 18 |
| learniq | 5 | 0 |
| pipelinq | 3 | 30 |
| portaliq | 3 | 0 |
| filinq | 1 | 1 |
| decidiq | 0 | 0 |
| integriq | 0 | 127 |
| openregister | 0 | 4 |

## Why a checked-in baseline

The header-action budget gate and others compare against the base ref only, and keep no file to go stale. This gate needs the list as well as the count. A count alone lets a pull request delete one Woo class and add one bezwaar class. The list makes the new file visible by name, and the count keeps the list from mattering when it is stale.
