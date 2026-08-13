#!/usr/bin/env bash
# SPDX-License-Identifier: EUPL-1.2
#
# Self-test for check_coding_standard_adoption.py (gate-65).
#
# Discovered and run by tests/run-helper-suites.sh — no workflow edit needed.
#
# Every assertion is paired: a NEGATIVE control (a compliant fixture must produce
# zero findings) and a POSITIVE control (a fixture carrying exactly one defect
# must produce exactly that finding). A checker that reports nothing on a broken
# repo and a checker that reports nothing on a clean one are the same program
# from the outside, which is the failure this suite exists to make impossible.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CHECKER="${HERE}/check_coding_standard_adoption.py"
WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

pass=0
fail=0

ok() { echo "  PASS  $1"; pass=$((pass + 1)); }
no() { echo "  FAIL  $1"; [ -n "${2:-}" ] && printf '        %s\n' "$2"; fail=$((fail + 1)); }

# Build a fully compliant app fixture in $1.
scaffold() {
    local d="$1"
    mkdir -p "$d/appinfo" "$d/lib"

    cat > "$d/.php-cs-fixer.dist.php" <<'PHP'
<?php
require_once __DIR__ . '/vendor/autoload.php';
$config = new Conduction\CodingStandard\Config();
$config->getFinder()->in(__DIR__ . '/lib');
return $config;
PHP

    cat > "$d/composer.json" <<'JSON'
{
    "name": "conductionnl/fixture",
    "require-dev": {
        "conduction/coding-standard": "^1.0",
        "nextcloud/ocp": "^34.0"
    },
    "scripts": {
        "cs:check": "php-cs-fixer fix --dry-run --diff",
        "cs:fix": "php-cs-fixer fix"
    }
}
JSON

    cat > "$d/phpcs.xml" <<'XML'
<?xml version="1.0"?>
<ruleset name="fixture">
    <file>lib</file>
    <rule ref="vendor/conduction/hydra-gates/quality-config/phpcs.xml"/>
</ruleset>
XML

    cat > "$d/.editorconfig" <<'EC'
root = true

[*]
charset = utf-8
indent_size = 4
indent_style = tab

[*.yml]
indent_size = 2
indent_style = space
EC

    cat > "$d/package.json" <<'JSON'
{
    "name": "fixture",
    "scripts": {
        "stylelint": "stylelint \"src/**/*.{vue,scss,css}\"",
        "stylelint:fix": "stylelint \"src/**/*.{vue,scss,css}\" --fix"
    }
}
JSON

    cat > "$d/phpmd.xml" <<'XML'
<?xml version="1.0"?>
<ruleset name="fixture">
    <rule ref="vendor/conduction/hydra-gates/quality-config/phpmd.xml"/>
</ruleset>
XML

    cat > "$d/phpstan.neon" <<'NEON'
includes:
    - vendor/conduction/hydra-gates/quality-config/phpstan-base.neon
    - phpstan-baseline.neon
NEON

    mkdir -p "$d/.github/workflows"
    cat > "$d/.github/workflows/code-quality.yml" <<'YML'
name: Code Quality
on: [push]
jobs:
  quality:
    uses: ConductionNL/.github/.github/workflows/quality.yml@main
    with:
      app-name: fixture
      nextcloud-test-refs: '["stable34", "stable32", "stable33"]'
      enable-hydra-gates: true
YML

    cat > "$d/appinfo/info.xml" <<'XML'
<?xml version="1.0"?>
<info>
    <id>fixture</id>
    <version>1.0.0</version>
    <dependencies>
        <nextcloud min-version="32" max-version="34"/>
    </dependencies>
</info>
XML
}

run() { python3 "$CHECKER" "$1" 2>&1; }

echo "check_coding_standard_adoption — self-test"
echo

# ── NEGATIVE CONTROL ──────────────────────────────────────────────────────
CLEAN="$WORK/clean"
scaffold "$CLEAN"
out="$(run "$CLEAN")"; rc=$?
if [ "$rc" -eq 0 ]; then
    ok "compliant fixture reports nothing (exit 0)"
else
    no "compliant fixture should be clean" "$out"
fi

if printf '%s' "$out" | grep -q 'checked [0-9]* rule'; then
    ok "prints its terminal summary line"
else
    no "no 'checked N rule(s)' summary — the runner reads its absence as a wiring failure" "$out"
fi

# ── POSITIVE CONTROLS: one defect at a time ───────────────────────────────
# Each names the defect it plants, so a broadened rule that starts matching
# everything is caught by the negative control above rather than hidden here.
probe() {
    local name="$1" expect="$2"; shift 2
    local d="$WORK/$name"
    rm -rf "$d"; scaffold "$d"
    # Every probe below passes its defect as ONE shell string (quoted sed/rm
    # commands), so the string form is what this has always meant. eval "$@"
    # only looked array-shaped — SC2294.
    ( cd "$d" && eval "$*" )
    local o; o="$(run "$d")"
    if printf '%s' "$o" | grep -q "FAIL ${expect}:"; then
        ok "detects ${name} (${expect})"
    else
        no "did not detect ${name}; expected 'FAIL ${expect}:'" "$o"
    fi
}

probe no-fixer-config          no-php-cs-fixer-config              'rm .php-cs-fixer.dist.php'
probe missing-autoloader       fixer-config-missing-autoloader     "sed -i '/autoload.php/d' .php-cs-fixer.dist.php"
probe cs-wired-to-phpcs        cs-script-wired-to-phpcs            "sed -i 's|php-cs-fixer fix --dry-run --diff|./vendor/bin/phpcs --standard=phpcs.xml|' composer.json"
probe nc-standard-direct       nextcloud-coding-standard-declared-directly \
                               "sed -i 's|\"conduction/coding-standard\": \"^1.0\",|\"conduction/coding-standard\": \"^1.0\", \"nextcloud/coding-standard\": \"^1.4\",|' composer.json"
probe phpcs-not-central        phpcs-not-centralised               "sed -i 's|vendor/conduction/hydra-gates/quality-config/phpcs.xml|PEAR|' phpcs.xml"
probe local-formatting-sniff   phpcs-declares-formatting-sniffs \
                               "sed -i 's|</ruleset>|<rule ref=\"Generic.WhiteSpace.ScopeIndent\"/></ruleset>|' phpcs.xml"
probe local-sniff-dir          local-custom-sniffs                 'mkdir -p phpcs-custom-sniffs/CustomSniffs'
probe no-editorconfig          no-editorconfig                     'rm .editorconfig'
probe editorconfig-spaces      editorconfig-not-tab                "sed -i 's|indent_style = tab|indent_style = space|' .editorconfig"
probe unquoted-glob            stylelint-glob-unquoted             "sed -i 's|stylelint \\\\\"src/\\*\\*/\\*.{vue,scss,css}\\\\\"|stylelint src/**/*.vue src/**/*.css|' package.json"
probe ocp-below-min            ocp-below-declared-minimum          "sed -i 's|\"nextcloud/ocp\": \"^34.0\"|\"nextcloud/ocp\": \"^31.0\"|' composer.json"

probe gates-ref-pinned         gates-ref-pinned                    "printf '      hydra-gates-ref: v1.3.0\\n' >> .github/workflows/code-quality.yml"
probe workflow-pinned          shared-workflow-pinned              "sed -i 's|quality.yml@main|quality.yml@v2.0.0|' .github/workflows/code-quality.yml"
probe package-pinned-exact     shared-package-pinned               "sed -i 's|\"conduction/coding-standard\": \"^1.0\"|\"conduction/coding-standard\": \"1.0.0\"|' composer.json"
probe package-pinned-branch    shared-package-pinned               "sed -i 's|\"conduction/coding-standard\": \"^1.0\"|\"conduction/coding-standard\": \"dev-some-branch\"|' composer.json"

probe phpmd-not-central        phpmd-not-centralised \
                               "sed -i 's|vendor/conduction/hydra-gates/quality-config/phpmd.xml|rulesets/codesize.xml|' phpmd.xml"
probe local-unusedparams       local-phpmd-unusedparams            'printf "<ruleset/>\n" > phpmd-unusedparams.xml'
probe phpstan-not-central      phpstan-not-centralised \
                               "sed -i '/phpstan-base.neon/d' phpstan.neon"
probe prettierrc-unwired       prettier-config-without-prettier    'printf "{}\n" > .prettierrc'
probe stylelintfix-unquoted    stylelint-glob-unquoted \
                               "sed -i 's|\"stylelint:fix\": \"stylelint \\\\\"src/\\*\\*/\\*.{vue,scss,css}\\\\\" --fix\"|\"stylelint:fix\": \"stylelint src/**/*.vue --fix\"|' package.json"

# ── PRETTIER IS NOT FORBIDDEN, ONLY UNWIRED PRETTIER ──────────────────────
# Nextcloud publishes @nextcloud/prettier-config and nextcloud/forms consumes it
# properly. A rule that failed every prettier config would push apps away from
# the aligned form, which is the opposite of this gate's purpose.
D="$WORK/prettierwired"
rm -rf "$D"; scaffold "$D"
printf '{}\n' > "$D/.prettierrc"
cat > "$D/package.json" <<'JSON'
{
    "name": "fixture",
    "devDependencies": {
        "@nextcloud/prettier-config": "^1.2.0",
        "prettier": "^3.9.6"
    },
    "scripts": {
        "format": "prettier --check .",
        "stylelint": "stylelint \"src/**/*.{vue,scss,css}\""
    }
}
JSON
out="$(run "$D")"
if printf '%s' "$out" | grep -q 'FAIL prettier-config-without-prettier:'; then
    no "a PROPERLY WIRED prettier config was reported — the rule cannot tell wired from inert" "$out"
else
    ok "accepts a prettier config that has prettier as a dependency"
fi

# ── A COMMENTED-OUT PHPSTAN INCLUDE IS NOT AN INCLUDE ─────────────────────
D="$WORK/phpstancommented"
rm -rf "$D"; scaffold "$D"
cat > "$D/phpstan.neon" <<'NEON'
includes:
    # - vendor/conduction/hydra-gates/quality-config/phpstan-base.neon
    - phpstan-baseline.neon
NEON
out="$(run "$D")"
if printf '%s' "$out" | grep -q 'FAIL phpstan-not-centralised:'; then
    ok "a commented-out phpstan include does not count as centralised"
else
    no "a COMMENTED-OUT phpstan include was accepted as centralised" "$out"
fi

# ── A DELIBERATE PHPMD DIVERGENCE IS STILL CENTRALISED ────────────────────
# exclude + re-declare is the sanctioned pattern for the six apps that diverge;
# failing it would make the rule unadoptable for exactly those apps.
D="$WORK/phpmddiverge"
rm -rf "$D"; scaffold "$D"
cat > "$D/phpmd.xml" <<'XML'
<?xml version="1.0"?>
<ruleset name="fixture">
    <rule ref="vendor/conduction/hydra-gates/quality-config/phpmd.xml">
        <exclude name="ShortVariable"/>
    </rule>
    <rule ref="rulesets/naming.xml/ShortVariable">
        <properties><property name="exceptions" value="x,y,h"/></properties>
    </rule>
</ruleset>
XML
out="$(run "$D")"
if printf '%s' "$out" | grep -q 'FAIL phpmd-not-centralised:'; then
    no "the sanctioned exclude+re-declare divergence was reported as not centralised" "$out"
else
    ok "accepts a deliberate divergence declared as exclude + re-declare"
fi

probe matrix-absent            test-matrix-not-declared \
                               "sed -i '/nextcloud-test-refs/d' .github/workflows/code-quality.yml"
probe matrix-misses-floor      test-matrix-misses-declared-versions \
                               "sed -i 's|\\[\\\"stable34\\\", \\\"stable32\\\", \\\"stable33\\\"\\]|[\\\"stable34\\\"]|' .github/workflows/code-quality.yml"
probe matrix-outside-range     test-matrix-tests-unsupported-version \
                               "sed -i 's|\\[\\\"stable34\\\", \\\"stable32\\\", \\\"stable33\\\"\\]|[\\\"stable31\\\", \\\"stable32\\\", \\\"stable33\\\", \\\"stable34\\\"]|' .github/workflows/code-quality.yml"

# ── A COMMENTED-OUT MATRIX IS NOT A MATRIX ────────────────────────────────
# The rule must not accept a declaration that only exists inside a comment.
D="$WORK/matrixcommented"
rm -rf "$D"; scaffold "$D"
sed -i "s|      nextcloud-test-refs: .*|      # nextcloud-test-refs: '[\"stable34\", \"stable32\", \"stable33\"]'|" "$D/.github/workflows/code-quality.yml"
# NOTE: capture first, then grep. `set -o pipefail` is on, and the checker exits
# with its VIOLATION COUNT — so `run | grep -q` returns non-zero on a successful
# match whenever the fixture is dirty, which is every positive control here.
out="$(run "$D")"
if printf '%s' "$out" | grep -q 'FAIL test-matrix-not-declared:'; then
    ok "a commented-out nextcloud-test-refs does not count as declared"
else
    no "a COMMENTED-OUT matrix was accepted as the declared matrix" "$out"
fi

# ── info.xml's RANGE MUST COME FROM THE ELEMENT, NOT A COMMENT ────────────
# procest's info.xml carries an explanatory comment containing a literal
# `<nextcloud min-version="28" .../>` ABOVE the live element. Reading the raw
# text returns 28 where the app declares 32 — which silently LOWERS the bar
# rules 9 and 11 enforce, the worst direction for a check to be wrong in.
D="$WORK/infocomment"
rm -rf "$D"; scaffold "$D"
cat > "$D/appinfo/info.xml" <<'XML'
<?xml version="1.0"?>
<info>
    <id>fixture</id>
    <version>1.0.0</version>
    <dependencies>
        <!-- History: this app once declared
             <nextcloud min-version="28" max-version="30"/>. It was true when
             written and is not any more. -->
        <nextcloud min-version="32" max-version="34"/>
    </dependencies>
</info>
XML
out="$(run "$D")"
if printf '%s' "$out" | grep -qE 'FAIL test-matrix-(misses-declared-versions|tests-unsupported-version):'; then
    no "the range was read from a COMMENT, not the live <nextcloud> element" "$out"
else
    ok "reads the declared range from the element, ignoring a commented-out one"
fi

# ...and the positive control for that same fixture: with the comment ignored,
# a matrix that covers 28-30 instead of 32-34 must still be caught. Without
# this, the assertion above would also pass on a checker that reads nothing.
D="$WORK/infocomment2"
rm -rf "$D"; scaffold "$D"
cat > "$D/appinfo/info.xml" <<'XML'
<?xml version="1.0"?>
<info>
    <id>fixture</id>
    <version>1.0.0</version>
    <dependencies>
        <!-- <nextcloud min-version="28" max-version="30"/> -->
        <nextcloud min-version="32" max-version="34"/>
    </dependencies>
</info>
XML
sed -i "s|      nextcloud-test-refs: .*|      nextcloud-test-refs: '[\"stable28\", \"stable29\", \"stable30\"]'|" "$D/.github/workflows/code-quality.yml"
out="$(run "$D")"
if printf '%s' "$out" | grep -q 'FAIL test-matrix-misses-declared-versions:'; then
    ok "a matrix matching only the commented-out range is still a finding"
else
    no "matrix covering the commented range was accepted" "$out"
fi

# ── ^1.0 IS NOT A PIN ─────────────────────────────────────────────────────
# The rule must distinguish "floats within a major" from "frozen". If it cannot,
# it fires on every compliant app and gets switched off.
D="$WORK/caret"
rm -rf "$D"; scaffold "$D"
if run "$D" | grep -q 'FAIL shared-package-pinned:'; then
    no "^1.0 was reported as a pin — the rule cannot tell floating from frozen"
else
    ok "treats ^1.0 as floating, not pinned"
fi

# ── hydra-gates-ref: main is the correct value, not a pin ─────────────────
D="$WORK/refmain"
rm -rf "$D"; scaffold "$D"
printf '      hydra-gates-ref: main\n' >> "$D/.github/workflows/code-quality.yml"
if run "$D" | grep -q 'FAIL gates-ref-pinned:'; then
    no "hydra-gates-ref: main was reported as a pin"
else
    ok "accepts an explicit hydra-gates-ref: main"
fi

# ── a COMMENTED-OUT pin is not a pin ──────────────────────────────────────
D="$WORK/commentedpin"
rm -rf "$D"; scaffold "$D"
printf '      # hydra-gates-ref: v1.3.0\n' >> "$D/.github/workflows/code-quality.yml"
if run "$D" | grep -q 'FAIL gates-ref-pinned:'; then
    no "a commented-out hydra-gates-ref was reported as a live pin"
else
    ok "ignores a commented-out hydra-gates-ref"
fi

# ── A COMMENTED-OUT RULE IS NOT A RULE ────────────────────────────────────
# gate-64's defect: grepping for a string matches it inside every comment.
D="$WORK/commented"
rm -rf "$D"; scaffold "$D"
sed -i 's|</ruleset>|<!-- <rule ref="Generic.WhiteSpace.ScopeIndent"/> --></ruleset>|' "$D/phpcs.xml"
if run "$D" | grep -q 'FAIL phpcs-declares-formatting-sniffs:'; then
    no "a COMMENTED-OUT formatting sniff was reported as live"
else
    ok "ignores a commented-out formatting sniff"
fi

# ── dev-master ocp is not below anything ──────────────────────────────────
D="$WORK/devmaster"
rm -rf "$D"; scaffold "$D"
sed -i 's|"nextcloud/ocp": "\^34.0"|"nextcloud/ocp": "dev-master"|' "$D/composer.json"
if run "$D" | grep -q 'FAIL ocp-below-declared-minimum:'; then
    no "nextcloud/ocp:dev-master reported as below the declared minimum"
else
    ok "treats nextcloud/ocp:dev-master as tracking the tip, not as stale"
fi

# ── a comment is not a config line (#415 class, #422) ─────────────────────
#
# `.php-cs-fixer.dist.php` was the one config in this module read RAW — the XML
# paths have been protected by strip_xml_comments() from the start, and its
# docstring already says why ("a commented-out rule is not a rule").
#
# Reverted against origin/main, the two FN arms below FLIP; the two
# anti-widening arms pass either way and are CONTROLS.
#
# The rule this silenced exists PRECISELY because a php-cs-fixer fatal reads
# exactly like a clean tree: with no autoloader the run dies "Class not found",
# and --format=json reports that as ZERO FILES NEEDING CHANGES. So the comment
# bought a green on the check whose job is to stop a green being bought.

rm -rf "$D"; scaffold "$D"
cat > "$D/.php-cs-fixer.dist.php" <<'PHP'
<?php
// TODO: we still need to require __DIR__ . '/vendor/autoload.php' here and
// switch to Conduction\CodingStandard\Config. Not done yet.
$config = new PhpCsFixer\Config();
return $config;
PHP
_out="$(run "$D")"
if printf '%s' "$_out" | grep -q 'FAIL fixer-config-missing-autoloader:' \
   && printf '%s' "$_out" | grep -q 'FAIL wrong-fixer-config:'; then
    ok "a TODO naming the autoloader and the shared Config satisfies neither rule"
else
    no "a TODO naming the missing lines silenced the fixer rules" "$_out"
fi

rm -rf "$D"; scaffold "$D"
cat > "$D/.php-cs-fixer.dist.php" <<'PHP'
<?php
/*
Historical: this file used to require __DIR__ . '/vendor/autoload.php'
and instantiate Conduction\CodingStandard\Config. It no longer does.
*/
return new PhpCsFixer\Config();
PHP
_out="$(run "$D")"
if printf '%s' "$_out" | grep -q 'FAIL fixer-config-missing-autoloader:'; then
    ok "a block comment describing what was REMOVED does not stand in for it"
else
    no "a removal note satisfied the autoloader rule" "$_out"
fi

# CONTROL (anti-widening), and the reason string contents are KEPT: the
# autoloader is required as `require __DIR__ . '/vendor/autoload.php'`, so the
# evidence IS a string literal. Under blank_strings=True this arm goes red and
# every correctly-configured repo in the fleet reports missing-autoloader.
rm -rf "$D"; scaffold "$D"
cat > "$D/.php-cs-fixer.dist.php" <<'PHP'
<?php
/*
Nextcloud's coding standard, via the shared Conduction config.
*/
require_once __DIR__ . '/vendor/autoload.php';
$config = new Conduction\CodingStandard\Config();
$config->getFinder()->in(__DIR__ . '/lib');
return $config;
PHP
_out="$(run "$D")"
if printf '%s' "$_out" | grep -qE 'FAIL (fixer-config-missing-autoloader|wrong-fixer-config):'; then
    no "a real config below a block comment was reported as missing its lines" "$_out"
else
    ok "a real require of a STRING path, below a block comment, still counts"
fi

# ── a crash must not read as clean ────────────────────────────────────────
if python3 "$CHECKER" "$WORK/does-not-exist" >/dev/null 2>&1; then
    no "a missing app root exited 0 — an unrunnable checker read as a clean repo"
else
    ok "a missing app root exits non-zero rather than reporting clean"
fi

echo
echo "----------------------------------------------------------------"
printf '%d passed, %d failed\n' "$pass" "$fail"
echo "----------------------------------------------------------------"
[ "$fail" -eq 0 ]
