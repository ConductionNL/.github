#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
# SPDX-FileCopyrightText: 2026 Conduction B.V. <info@conduction.nl>
"""Detect the OBSOLETE x-openregister-notifications dialect (ADR-031).

Backs hydra-gate-notification-dialect check (a). Given one or more
``lib/Settings/*register*.json`` files, this helper JSON-parses each one,
walks every schema's ``x-openregister-notifications`` block, and reports any
legacy-dialect token found *inside that block*.

Scoping the scan to the notification block (rather than grepping the whole
register file) is what keeps the gate precise: a register routinely contains
``@self.`` inside ``x-openregister-aggregations`` filters and a ``"channel"``
property on an unrelated schema. Those are NOT legacy notification dialect and
must not be flagged. Whole-file grep false-positives on real apps (decidesk,
scholiq) — verified 2026-05-26 — and a gate that false-positives gets disabled.

Legacy tokens (see ADR-031 — canonical dialect uses plural ``channels`` /
``recipients`` arrays, ``trigger.type``, and a per-locale ``subject`` map):
  - ``lifecycleEnter``        legacy trigger key
  - ``calculated``            legacy trigger key (now ``calculatedChange``)
  - ``alsoDispatchLifecycle`` legacy side-channel flag
  - ``idempotencyKey``        legacy dedupe field
  - ``@self.``                legacy recipient/self reference inside a rule
  - singular ``channel``      (rule-level; canonical is ``channels``)
  - singular ``recipient``    (rule-level; canonical is ``recipients``)

Output: one ``<file>: rule=<ruleKey> token=<token>`` line per finding on
stdout. Exit code is always 0; the bash gate counts the printed lines (this
mirrors the diff-scope-friendly contract of the other lib/ helpers). A file
that is not valid JSON, or has no notification blocks, contributes nothing.
"""

from __future__ import annotations

import json
import sys

# WHERE EACH TOKEN CAN ACTUALLY LIVE (#424).
#
# These four were matched against `json.dumps(rule)` — one flat haystack in
# which a KEY, a machine value and a sentence of human documentation are the
# same bytes. So a rule whose own `description` WARNED AGAINST the legacy
# dialect was reported as the legacy dialect:
#
#   "description": "Canonical dialect. Do NOT use the legacy lifecycleEnter
#                   trigger or alsoDispatchLifecycle; removed in ADR-031."
#     -> rule=onIntakeClosed token=lifecycleEnter
#        rule=onIntakeClosed token=alsoDispatchLifecycle
#
# The better the register is documented, the redder the repo — the exact shape
# recorded for gate-58 in source_scope's header, in a file format where the
# fix is not a mask but reading the STRUCTURE instead of its serialisation.
#
# Three of the four are KEY names in the dialect (`trigger.lifecycleEnter`,
# rule-level `alsoDispatchLifecycle` / `idempotencyKey`); `@self.` is a
# recipient VALUE. Nothing that was a key-hit or a machine-value hit before is
# lost — only the prose axis is.
_KEY_TOKENS = (
    "lifecycleEnter",
    "alsoDispatchLifecycle",
    "idempotencyKey",
)
_VALUE_TOKENS = (
    "@self.",
)
# Fields whose contents are human text, per ADR-031: `subject` is the
# per-locale message map the CANONICAL dialect requires, and the rest are
# documentation. Prose about the dialect is not the dialect.
_PROSE_FIELDS = frozenset({
    "description", "title", "subject", "comment", "$comment",
})


def _keys_and_values(node, in_prose=False, keys=None, values=None):
    """Every KEY name and every machine string VALUE reachable from *node*.

    Anything under a prose field is neither: its keys are locale codes and its
    values are sentences.
    """
    if keys is None:
        keys, values = [], []
    if isinstance(node, dict):
        for key, val in node.items():
            if not in_prose:
                keys.append(key)
            _keys_and_values(val, in_prose or key in _PROSE_FIELDS, keys, values)
    elif isinstance(node, list):
        for item in node:
            _keys_and_values(item, in_prose, keys, values)
    elif isinstance(node, str) and not in_prose:
        values.append(node)
    return keys, values


def _iter_notification_blocks(data):
    """Yield (schema_name, notifications_dict) for every schema that declares
    an x-openregister-notifications block. Tolerant of shapes: the block lives
    under components.schemas.<Schema>, but some register files nest schemas
    directly at the top level, so we also scan there as a fallback."""
    seen = set()
    schemas = {}
    comp = data.get("components") if isinstance(data, dict) else None
    if isinstance(comp, dict) and isinstance(comp.get("schemas"), dict):
        schemas.update(comp["schemas"])
    # Fallback: top-level schema map (register files that omit components).
    if isinstance(data, dict):
        for key, val in data.items():
            if isinstance(val, dict) and "x-openregister-notifications" in val:
                schemas.setdefault(key, val)
    for sname, sch in schemas.items():
        if not isinstance(sch, dict):
            continue
        notif = sch.get("x-openregister-notifications")
        if isinstance(notif, dict) and sname not in seen:
            seen.add(sname)
            yield sname, notif


def _scan_rule(rule_key, rule):
    """Return a list of legacy tokens found in a single notification rule."""
    findings = []
    if not isinstance(rule, dict):
        return findings
    # Rule-level singular keys — canonical dialect uses the plural arrays.
    if "channel" in rule and "channels" not in rule:
        findings.append("channel")
    if "recipient" in rule and "recipients" not in rule:
        findings.append("recipient")
    # Legacy trigger key: trigger.calculated → canonical trigger.type
    # 'calculatedChange'. Only flag 'calculated' as a trigger key, not a
    # substring of 'calculatedChange'.
    trig = rule.get("trigger")
    if isinstance(trig, dict) and "calculated" in trig:
        findings.append("trigger.calculated")
    # Structural tokens — see _KEY_TOKENS / _VALUE_TOKENS for why this is not
    # a substring search over `json.dumps(rule)` any more.
    keys, values = _keys_and_values(rule)
    for tok in _KEY_TOKENS:
        if any(tok in key for key in keys):
            findings.append(tok)
    for tok in _VALUE_TOKENS:
        if any(tok in val for val in values) or any(tok in key for key in keys):
            findings.append(tok)
    return findings


def scan_file(path):
    """Return a list of '<path>: rule=<key> token=<token>' finding strings."""
    out = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        # Unreadable / invalid JSON → out of this gate's scope.
        return out
    for _sname, notif in _iter_notification_blocks(data):
        for rule_key, rule in notif.items():
            for tok in _scan_rule(rule_key, rule):
                out.append(f"{path}: rule={rule_key} token={tok}")
    return out


def main(argv):
    findings = []
    for path in argv[1:]:
        findings.extend(scan_file(path))
    for line in findings:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
