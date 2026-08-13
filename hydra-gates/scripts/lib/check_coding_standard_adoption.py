#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Conduction
# SPDX-License-Identifier: EUPL-1.2
"""
gate-65: coding-standard-adoption.

Conduction code must pass ``nextcloud/coding-standard`` unchanged. We may be
stricter than Nextcloud; we may not be different from it. This checker is what
makes that a rule rather than an intention.

WHY IT EXISTS
-------------
Measured 2026-08-12 across the 18 core apps, from canonical
``<app>@development``. ``psalm.xml``, ``phpstan.neon``, ``playwright.config.ts``
and ``code-quality.yml`` each existed in EIGHTEEN mutually different versions.
``NamedParametersSniff.php`` — a custom *rule*, not a setting — existed in six,
one of which called ``addWarning()`` where the others called ``addError()``.

None of that was anyone's decision. Every one of those files started as a copy
of something shared, and copies drift. Centralising them does not by itself fix
that; the 18 variants were copies of something shared too. What stops it
recurring is a check that fails when an app walks away from the centre.

Each rule below corresponds to a defect that was live in the fleet, not to a
preference:

  1. NO PHP-CS-FIXER CONFIG — all 1,427 openregister files failed Nextcloud's
     standard because nothing ever ran it.
  2. MISSING AUTOLOADER in .php-cs-fixer.dist.php — php-cs-fixer includes that
     file before the app's autoloader, so the config fatals with "Class not
     found"; in --format=json that fatal is reported as ZERO FILES NEEDING
     CHANGES. It reads exactly like a clean tree.
  3. cs:check / cs:fix WIRED TO PHPCS — those are nextcloud/coding-standard's
     script names. In this fleet they were aliases for phpcs/phpcbf, so the
     documented Nextcloud command reformatted code AWAY from Nextcloud.
  4. nextcloud/coding-standard AS A DIRECT DEPENDENCY — 17 of 18 apps declared
     it with no config file and no invocation anywhere. It must arrive
     transitively, at a version conduction/coding-standard has tested against.
  5. LOCAL FORMATTING SNIFFS — two formatters with overlapping jurisdiction make
     an app UNFIXABLE: `cs:fix` and `phpcs` demand opposite things and neither
     can be satisfied. Running the old PEAR ruleset over php-cs-fixer-formatted
     code produced 111,932 findings, 111,747 of them formatting.
  6. A LOCAL phpcs-custom-sniffs/ COPY — the six-versions-of-one-rule defect.
  7. NO .editorconfig — no fleet app had one, so an editor configured by
     someone's previous Nextcloud work defaulted to tabs, which the old ruleset
     then rejected. Nextcloud core ships one.
  8. UNQUOTED STYLELINT GLOB — 13 apps ran `stylelint src/**/*.vue …` unquoted,
     so the SHELL expanded it and without globstar `src/**/` matched exactly one
     directory level. Nested components were silently unlinted.
  9. nextcloud/ocp BELOW info.xml's min-version — 15 apps declared NC 32-34 and
     analysed against ^31. Nothing ADDED in 32/33/34 was visible, and — the part
     that bites — nothing REMOVED was reportable either. That is why the NC 34
     removal of \\OC::$server needed a hand-written PHPCS sniff.
 10. A PINNED SHARED STANDARD — the gates, the coding standard and the shared
     workflow are consumed at the tip, never at a version. A pin is a silent
     expiry date, and this fleet has paid for it twice in the same year:

       .github#159  22 repos sat on gate package v1.0.1 while 16 gates were
                    DEAD fleet-wide — and every one of them reported PASS.
       .github#173  a default flipped at @main then reached those same old
                    runners and turned them red on gates whose subject matter
                    they had no code for.

     Both directions of that failure come from the same cause: two halves of one
     system moving independently. `^1.0` is not a pin — it floats within a major
     and is correct. An exact version, a `dev-<branch>` constraint, or a
     `hydra-gates-ref` that is not `main`, is.
 11. A TEST MATRIX THAT DISAGREES WITH info.xml — the range in info.xml is a
     promise to the App Store, and `nextcloud-test-refs` is the only thing that
     can redeem it. This fleet broke that promise in BOTH directions inside one
     programme: first 18 apps declared 32-34 and tested 31/32, so nothing ran on
     the version being adopted; then the migration that fixed it REPLACED the
     list with `'["stable34"]'` instead of extending it, and 16 apps stopped
     testing their own declared floor. The second defect was introduced by the
     change that fixed the first, and no check noticed either.

     The out-of-range half is not merely wasteful. A stable31 leg survived long
     after openregister raised its floor to 32, so `occ app:enable openregister`
     failed with only a ::warning::, the run continued with no data layer, and
     every /apps/openregister/... call returned Nextcloud's HTML 404 page. That
     leg's red said nothing and its green said less.

USAGE
    check_coding_standard_adoption.py <app-root>

Prints one `FAIL <rule>: <detail>` line per violation, then a terminal summary
`checked N rule(s)`. The runner treats a missing summary as a WIRING failure
rather than a pass, so a crash cannot be mistaken for a clean repo.

Exit code is the violation count (0 = clean, 90 = could not run).
"""

from __future__ import annotations

import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from source_scope import php_mask  # noqa: E402

CENTRAL_RULESET = "quality-config/phpcs.xml"
CENTRAL_PHPMD = "quality-config/phpmd.xml"
CENTRAL_PHPSTAN = "quality-config/phpstan-base.neon"

# Sniff families php-cs-fixer owns. A phpcs.xml that names one locally is
# re-opening the jurisdiction conflict rule 5 describes. Matched against the
# `ref=` of a <rule>, so `Generic.WhiteSpace.ScopeIndent` and
# `Squiz.WhiteSpace.OperatorSpacing` both hit on `WhiteSpace`.
FORMATTING_TOKENS = (
    "WhiteSpace",
    "Whitespace",
    "ScopeIndent",
    "ArrayIndent",
    "Indent",
    "SpaceAfterCast",
    "ConcatenationSpacing",
    "MultipleStatementAlignment",
    "ClassDeclaration",
    "FunctionDeclaration",
    "ElseIfDeclaration",
    "DocCommentAlignment",
    "OpeningBrace",
    "ClosingBrace",
    "LineEndings",
    "DisallowTabIndent",
    "DisallowSpaceIndent",
)


def read(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except OSError:
        return None


def strip_xml_comments(xml: str) -> str:
    """A commented-out rule is not a rule. Matching one would be the
    grep-a-string-and-hit-every-comment defect gate-64 was written about."""
    return re.sub(r"<!--.*?-->", "", xml, flags=re.S)


def check(root: str) -> tuple[list[str], int]:
    fails: list[str] = []
    checked = 0

    def fail(rule: str, detail: str) -> None:
        fails.append(f"FAIL {rule}: {detail}")

    def j(name: str):
        raw = read(os.path.join(root, name))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            fail("unparseable-json", f"{name} is not valid JSON ({exc}).")
            return None

    composer = j("composer.json")
    package = j("package.json")

    # ── 1 + 2. php-cs-fixer config ───────────────────────────────────────
    checked += 1
    fixer = read(os.path.join(root, ".php-cs-fixer.dist.php")) or read(
        os.path.join(root, ".php-cs-fixer.php")
    )
    if fixer is None:
        fail(
            "no-php-cs-fixer-config",
            "no .php-cs-fixer.dist.php. Nothing in this repo runs Nextcloud's "
            "coding standard, so nothing can be said about whether it passes it.",
        )
    else:
        # A COMMENT SAYING YOU STILL OWE THE LINE IS NOT THE LINE (#422).
        #
        # The XML paths in this module are protected by strip_xml_comments()
        # for exactly this reason, and its docstring says so: "a commented-out
        # rule is not a rule". `.php-cs-fixer.dist.php` was the one config read
        # RAW. Measured on this checker, one fixture, two lines added:
        #
        #     a fixer config with neither the autoloader nor the shared Config
        #       -> FAIL — fixer-config-missing-autoloader          (correct)
        #     + "// TODO: we still need to require __DIR__ . '/vendor/autoload.php'
        #        // here and switch to Conduction\CodingStandard\Config.
        #        // Not done yet."
        #       -> PASS on both rules                              <- the defect
        #
        # The rule it silenced exists PRECISELY because a php-cs-fixer fatal
        # reads exactly like a clean tree: with no autoloader the run dies with
        # "Class not found", and `--format=json` reports that as ZERO FILES
        # NEEDING CHANGES. So the comment bought a green on the check whose job
        # is to stop a green being bought.
        #
        # ⚠️ STRING CONTENTS ARE KEPT (`php_mask` default), and here that is
        # not a preference — the evidence IS a string. The autoloader is
        # required as `require __DIR__ . '/vendor/autoload.php'`, and blanking
        # literals would delete the path the regex matches on, failing every
        # correctly-configured repo in the fleet.
        fixer = php_mask(fixer)
        if "Conduction\\CodingStandard\\Config" not in fixer and "CodingStandard\\Config" not in fixer:
            fail(
                "wrong-fixer-config",
                ".php-cs-fixer.dist.php does not instantiate "
                "Conduction\\CodingStandard\\Config.",
            )
        checked += 1
        if not re.search(r"require(_once)?\s.*autoload\.php", fixer):
            fail(
                "fixer-config-missing-autoloader",
                ".php-cs-fixer.dist.php never requires vendor/autoload.php. "
                "php-cs-fixer includes this file before the app's autoloader, so "
                "it fatals with \"Class not found\" — and in --format=json that "
                "fatal is reported as ZERO FILES NEEDING CHANGES, which reads "
                "exactly like a clean tree.",
            )

    # ── 3 + 4. composer wiring ───────────────────────────────────────────
    if composer is not None:
        req = {}
        req.update(composer.get("require") or {})
        req.update(composer.get("require-dev") or {})
        scripts = composer.get("scripts") or {}

        checked += 1
        if "conduction/coding-standard" not in req:
            fail(
                "coding-standard-not-required",
                "composer.json does not require conduction/coding-standard.",
            )

        checked += 1
        if "nextcloud/coding-standard" in req:
            fail(
                "nextcloud-coding-standard-declared-directly",
                "nextcloud/coding-standard is a DIRECT dependency. It must arrive "
                "transitively through conduction/coding-standard, at a version that "
                "package has tested against. Declared directly it was, in 17 of 18 "
                "apps, a dead dependency with no config and no invocation — loaded, "
                "and ready to reformat everything for whoever found it.",
            )

        checked += 1
        for name in ("cs:check", "cs:fix"):
            body = scripts.get(name)
            if body is None:
                fail(
                    "cs-script-missing",
                    f"composer.json declares no '{name}' script.",
                )
                continue
            body_s = body if isinstance(body, str) else " ".join(body)
            if "phpcbf" in body_s or re.search(r"\bphpcs\b", body_s):
                fail(
                    "cs-script-wired-to-phpcs",
                    f"'{name}' runs PHPCS, not php-cs-fixer. That is "
                    "nextcloud/coding-standard's script name, so a contributor "
                    "running the documented Nextcloud command gets this fleet's "
                    f"reformatting instead. Body: {body_s!r}",
                )
            elif "php-cs-fixer" not in body_s:
                fail(
                    "cs-script-runs-neither",
                    f"'{name}' invokes neither php-cs-fixer nor phpcs: {body_s!r}",
                )

    # ── 5 + 6. PHPCS keeps to semantics ──────────────────────────────────
    phpcs_raw = read(os.path.join(root, "phpcs.xml")) or read(
        os.path.join(root, "phpcs.xml.dist")
    )
    if phpcs_raw is not None:
        body = strip_xml_comments(phpcs_raw)

        checked += 1
        if CENTRAL_RULESET not in body:
            fail(
                "phpcs-not-centralised",
                f"phpcs.xml does not reference {CENTRAL_RULESET}. Every app that "
                "kept its own full ruleset is how this fleet reached six variants "
                "of one file.",
            )

        checked += 1
        local_formatting = []
        for ref in re.findall(r'<rule\s+ref="([^"]+)"', body):
            if ref.startswith("vendor/") or ref.startswith("./") or ref.startswith("../"):
                continue
            if any(tok in ref for tok in FORMATTING_TOKENS):
                local_formatting.append(ref)
        if local_formatting:
            fail(
                "phpcs-declares-formatting-sniffs",
                "phpcs.xml names formatting sniffs that php-cs-fixer owns: "
                + ", ".join(sorted(set(local_formatting)))
                + ". Two formatters with overlapping jurisdiction make an app "
                "unfixable — cs:fix and phpcs then demand opposite things and "
                "neither can be satisfied.",
            )

    checked += 1
    if os.path.isdir(os.path.join(root, "phpcs-custom-sniffs")):
        fail(
            "local-custom-sniffs",
            "phpcs-custom-sniffs/ exists locally. The sniffs come from "
            "vendor/conduction/hydra-gates/. A local copy is how "
            "NamedParametersSniff.php reached six versions across the fleet, one "
            "of them calling addWarning() where the rest called addError().",
        )

    # ── 7. .editorconfig ─────────────────────────────────────────────────
    checked += 1
    editorconfig = read(os.path.join(root, ".editorconfig"))
    if editorconfig is None:
        fail(
            "no-editorconfig",
            "no .editorconfig. Nextcloud core ships one; without it an editor "
            "falls back to whatever the developer last configured.",
        )
    else:
        # The [*] section's indent_style. A file that sets it to space for PHP
        # contradicts the formatter it is supposed to agree with.
        star = re.search(r"^\[\*\]\s*$(.*?)(?=^\[|\Z)", editorconfig, re.M | re.S)
        style = None
        if star:
            m = re.search(r"^\s*indent_style\s*=\s*(\w+)", star.group(1), re.M)
            style = m.group(1) if m else None
        if style != "tab":
            fail(
                "editorconfig-not-tab",
                f"[*] indent_style is {style!r}, not 'tab'. Nextcloud's own "
                ".editorconfig sets tab, and php-cs-fixer enforces it — an "
                ".editorconfig that disagrees fights the formatter on every save.",
            )

    # ── 8. stylelint glob ────────────────────────────────────────────────
    # BOTH scripts, not just `stylelint`. Measured on launchpad: `stylelint` was
    # correctly quoted while `stylelint:fix` was not, so the autofix covered a
    # NARROWER set than the check — `npm run stylelint:fix` reports done and
    # leaves violations the gate then flags. An earlier revision of this rule
    # inspected only the check script and reported that app as clean.
    if package is not None:
        for script_name in ("stylelint", "stylelint:fix"):
            sl = (package.get("scripts") or {}).get(script_name)
            if not sl:
                continue
            checked += 1
            # Everything after the binary name. An unquoted glob containing `**`
            # is expanded by the SHELL, and without globstar `src/**/` matches
            # exactly one directory level.
            args = sl.split("stylelint", 1)[1] if "stylelint" in sl else sl
            for token in args.split():
                if "**" in token and not (
                    token.startswith(("'", '"')) or token.endswith(("'", '"'))
                ):
                    fail(
                        "stylelint-glob-unquoted",
                        f"the '{script_name}' script passes an unquoted glob "
                        f"{token!r}. The shell expands it, and without globstar "
                        "`src/**/` matches exactly one directory level — nested "
                        "components are silently not linted. Quote it so stylelint "
                        "expands it.",
                    )
                    break

    # ── 12 + 13. PHPMD comes from the package ────────────────────────────
    # The same argument as rules 5/6, for the other analyser. 18 mutually
    # different copies of one ruleset is what the fleet had; six of them differed
    # in ways nobody had decided, and one carried a rule that was DEAD (launchpad
    # set DevelopmentCodeFragment ignore-namespaces=false while every class in the
    # repo is namespaced).
    phpmd_raw = read(os.path.join(root, "phpmd.xml"))
    if phpmd_raw is not None:
        checked += 1
        if CENTRAL_PHPMD not in strip_xml_comments(phpmd_raw):
            fail(
                "phpmd-not-centralised",
                f"phpmd.xml does not reference {CENTRAL_PHPMD}. A deliberate "
                "divergence is allowed and expected — declare it as "
                '<rule ref="…central…"><exclude name="X"/></rule> plus a '
                "re-declared X with this app's properties, so the deviation is "
                "visible as a deviation instead of hiding inside a full copy.",
            )

    checked += 1
    if os.path.isfile(os.path.join(root, "phpmd-unusedparams.xml")):
        fail(
            "local-phpmd-unusedparams",
            "phpmd-unusedparams.xml exists locally. It comes from "
            "vendor/conduction/hydra-gates/quality-config/. The `phpmd` script "
            "runs two rulesets and keeps the worst exit code; point its second "
            "leg at the vendored file and delete this copy.",
        )

    # ── 14. PHPStan includes the shared base ─────────────────────────────
    phpstan_raw = read(os.path.join(root, "phpstan.neon")) or read(
        os.path.join(root, "phpstan.neon.dist")
    )
    if phpstan_raw is not None:
        checked += 1
        body = re.sub(r"^\s*#.*$", "", phpstan_raw, flags=re.M)
        if CENTRAL_PHPSTAN not in body:
            fail(
                "phpstan-not-centralised",
                f"phpstan.neon does not include {CENTRAL_PHPSTAN}. Keep only this "
                "app's own baseline include and ignores naming symbols no other "
                "app has. NOTE: this requires conduction/hydra-gates >= v1.7.1 — "
                "v1.7.0's base declared bare relative paths, and PHPStan resolves "
                "those against the file that DECLARES them, so `paths: lib` became "
                "vendor/…/quality-config/lib and the run aborted.",
            )

    # ── 15. no unreferenced prettier config ──────────────────────────────
    # Nextcloud publishes @nextcloud/prettier-config and nextcloud/forms consumes
    # it properly — prettier + eslint-config-prettier + a real `format` script. So
    # prettier is not forbidden; an UNWIRED prettier config is.
    #
    # What the fleet had was neither: a hand-rolled .prettierrc setting 2-space
    # indent and double quotes — the OPPOSITE of @nextcloud/prettier-config's
    # useTabs/singleQuote — with no dependency, no script and no CI leg. Inert
    # where it would help, active in editors, where every save produced code
    # @nextcloud/eslint-config then rejected.
    if package is not None:
        deps = {}
        deps.update(package.get("dependencies") or {})
        deps.update(package.get("devDependencies") or {})
        has_prettier = any(d == "prettier" or d.endswith("/prettier-config") for d in deps)
        configs = [
            f
            for f in (
                ".prettierrc",
                ".prettierrc.json",
                ".prettierrc.js",
                ".prettierrc.cjs",
                "prettier.config.js",
                "prettier.config.cjs",
            )
            if os.path.isfile(os.path.join(root, f))
        ]
        if configs:
            checked += 1
            if not has_prettier:
                fail(
                    "prettier-config-without-prettier",
                    f"{', '.join(configs)} exists but neither prettier nor a "
                    "*/prettier-config package is a dependency, so nothing in CI "
                    "ever runs it. It still applies in editors, which is the worst "
                    "of both: contributors get their files reformatted into a state "
                    "the linter rejects. Either delete it, or adopt it properly the "
                    "way nextcloud/forms does — @nextcloud/prettier-config + "
                    "prettier + eslint-config-prettier + a format script and a CI "
                    "leg.",
                )

    # ── 9. ocp major vs info.xml min-version ─────────────────────────────
    info = read(os.path.join(root, "appinfo", "info.xml"))
    if info is not None and composer is not None:
        # Comments FIRST. procest's info.xml carries an explanatory comment
        # containing a literal `<nextcloud min-version="28" .../>` describing an
        # older declaration, and it sits ABOVE the live element — so a search of
        # the raw text returns 28 where the app declares 32. That does not fail
        # loudly; it silently RAISES the bar this rule will accept, which is the
        # worst direction for a check to be wrong in.
        m = re.search(r'<nextcloud[^>]*min-version="(\d+)"', strip_xml_comments(info))
        req = {}
        req.update(composer.get("require") or {})
        req.update(composer.get("require-dev") or {})
        ocp = req.get("nextcloud/ocp")
        if m and ocp:
            checked += 1
            declared_min = int(m.group(1))
            om = re.search(r"(\d+)", ocp)
            # `dev-master` and friends track the tip; they cannot be below the
            # declared minimum, so they are not a finding.
            if om and not ocp.strip().startswith("dev-"):
                ocp_major = int(om.group(1))
                if ocp_major < declared_min:
                    fail(
                        "ocp-below-declared-minimum",
                        f"appinfo/info.xml declares min-version=\"{declared_min}\" "
                        f"but composer pins nextcloud/ocp:{ocp}. Static analysis is "
                        f"reading the NC {ocp_major} API surface, a major below what "
                        "this app claims to support — so nothing added in "
                        f"{declared_min}+ is visible to it, and nothing REMOVED in "
                        f"{declared_min}+ can be reported. That is why the NC 34 "
                        "removal of \\OC::$server needed a hand-written sniff.",
                    )

    # ── 10. nothing shared may be pinned ─────────────────────────────────
    # An exact version, or a dev-branch constraint, freezes this app against a
    # standard the rest of the fleet has moved past. `^1.0` floats and is fine.
    if composer is not None:
        req = {}
        req.update(composer.get("require") or {})
        req.update(composer.get("require-dev") or {})
        for pkg in ("conduction/coding-standard", "conduction/hydra-gates"):
            spec = req.get(pkg)
            if not spec:
                continue
            checked += 1
            s = spec.strip()
            if s.startswith("dev-"):
                fail(
                    "shared-package-pinned",
                    f"{pkg} is constrained to {s!r} — a branch, not a released "
                    "range. This app is frozen against whatever that branch "
                    "happens to contain and will not follow the fleet. Use a "
                    "floating range such as ^1.0.",
                )
            elif re.fullmatch(r"v?\d+(\.\d+){1,2}", s) or s.startswith("=="):
                fail(
                    "shared-package-pinned",
                    f"{pkg} is pinned to the exact version {s!r}. A pin is a "
                    "silent expiry date: 22 repos once sat on gate package v1.0.1 "
                    "while 16 gates were dead fleet-wide and every one reported "
                    "PASS (.github#159). Use ^1.0.",
                )

    # The shared workflow and the gate package are consumed at the tip. A caller
    # that names a tag stops receiving fixes AND keeps receiving new defaults
    # from the half of the system it did not pin — the #173 direction.
    wf = read(os.path.join(root, ".github", "workflows", "code-quality.yml"))
    if wf is not None:
        body = re.sub(r"^\s*#.*$", "", wf, flags=re.M)

        checked += 1
        m = re.search(r"^\s*hydra-gates-ref:\s*[\"']?([^\s\"'#]+)", body, re.M)
        if m and m.group(1) != "main":
            fail(
                "gates-ref-pinned",
                f"hydra-gates-ref is set to {m.group(1)!r}. The gate package is "
                "consumed at main, together with the shared workflow that drives "
                "it, so a gate fix reaches this repo without a commit in this "
                "repo. Pinned, the two halves move independently: an old runner "
                "receives a new default and goes red on gates it has no subject "
                "matter for (.github#173), or silently stops running gates it "
                "never learned about (#159). Remove the input.",
            )

        checked += 1
        for ref in re.findall(
            r"uses:\s*ConductionNL/\.github/\.github/workflows/[^@\s]+@([^\s]+)", body
        ):
            if ref != "main":
                fail(
                    "shared-workflow-pinned",
                    f"the shared quality workflow is consumed at @{ref}, not @main. "
                    "A pinned pipeline stops receiving fixes for defects found in "
                    "other apps — which is the entire reason it is shared.",
                )
                break

        # ── 11. the tested matrix covers the declared range ──────────────
        # An app's appinfo/info.xml is a PROMISE to the App Store: these server
        # majors work. `nextcloud-test-refs` is the only thing that can redeem
        # it. When they disagree, the promise is the part users act on and the
        # matrix is the part that would have caught it being wrong.
        #
        # This fleet has now made that mistake in BOTH directions inside one
        # programme. First every app declared 32-34 and tested 31/32, so nothing
        # was ever exercised on the version being adopted. Then the migration
        # that fixed it REPLACED the list with '["stable34"]' instead of
        # extending it, and 16 apps stopped testing their own declared floor.
        # Same defect, opposite end, and the second one was introduced by the
        # change that fixed the first.
        #
        # A leg OUTSIDE the range is the other half of the rule, and it is not
        # merely wasteful: the fleet ran a stable31 leg long after openregister
        # raised its floor to 32, so `occ app:enable openregister` failed with
        # only a ::warning::, the run continued with no data layer, and every
        # /apps/openregister/... call returned Nextcloud's HTML 404 page. That
        # leg's red said nothing, and its green said less.
        if info is not None:
            info_body = strip_xml_comments(info)
            lo = re.search(r'<nextcloud[^>]*\bmin-version="(\d+)"', info_body)
            hi = re.search(r'<nextcloud[^>]*\bmax-version="(\d+)"', info_body)
            if lo and hi:
                checked += 1
                declared = set(range(int(lo.group(1)), int(hi.group(1)) + 1))
                rm = re.search(
                    r"^\s*nextcloud-test-refs:\s*'(\[[^']*\])'", body, re.M
                )
                if rm is None:
                    fail(
                        "test-matrix-not-declared",
                        f"appinfo/info.xml declares NC "
                        f"{lo.group(1)}-{hi.group(1)} but code-quality.yml passes "
                        "no nextcloud-test-refs, so the matrix is whatever the "
                        "shared workflow currently defaults to. A default cannot "
                        "know this app's declared range; state the range here.",
                    )
                else:
                    try:
                        refs = json.loads(rm.group(1))
                    except json.JSONDecodeError as exc:
                        fail(
                            "test-matrix-unparseable",
                            f"nextcloud-test-refs is not valid JSON ({exc}): "
                            f"{rm.group(1)!r}. The workflow calls fromJSON() on "
                            "it, so this fails at matrix expansion.",
                        )
                        refs = []
                    tested = {
                        int(r[len("stable") :])
                        for r in refs
                        if isinstance(r, str) and re.fullmatch(r"stable\d+", r)
                    }
                    missing = sorted(declared - tested)
                    outside = sorted(tested - declared)
                    if missing:
                        fail(
                            "test-matrix-misses-declared-versions",
                            f"appinfo/info.xml declares NC "
                            f"{lo.group(1)}-{hi.group(1)}, but no job runs on "
                            + ", ".join(f"stable{v}" for v in missing)
                            + f". The matrix is {refs!r}. Those majors are "
                            "advertised to the App Store and exercised by "
                            "nothing — not known-broken, unmeasured. Either add "
                            "the legs or narrow what info.xml claims.",
                        )
                    if outside:
                        fail(
                            "test-matrix-tests-unsupported-version",
                            "the matrix runs on "
                            + ", ".join(f"stable{v}" for v in outside)
                            + f", outside the declared range {lo.group(1)}-"
                            f"{hi.group(1)}. A leg on a version the app does not "
                            "support cannot pass for the right reason, and this "
                            "fleet has had one pass for the wrong one.",
                        )

    return fails, checked


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: check_coding_standard_adoption.py <app-root>", file=sys.stderr)
        return 90

    root = sys.argv[1]
    if not os.path.isdir(root):
        print(f"not a directory: {root}", file=sys.stderr)
        return 90

    try:
        fails, checked = check(root)
    except Exception as exc:  # noqa: BLE001 - a crash must not read as clean
        print(f"checker crashed: {exc!r}", file=sys.stderr)
        return 90

    for line in fails:
        print(line)

    # Terminal summary. The runner treats its absence as a WIRING failure, so a
    # crash can never be mistaken for a clean repo.
    print(f"checked {checked} rule(s)")
    return len(fails)


if __name__ == "__main__":
    sys.exit(main())
