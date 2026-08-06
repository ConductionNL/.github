#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Gate-40 form-label-association — every form control must have an
accessible name (WCAG 2.2 AA, SC 1.3.1 Info and Relationships and SC 3.3.2
Labels or Instructions).

WHY THIS WAS REWRITTEN
----------------------
The previous implementation flattened the file's newlines into spaces and
ran four independent regexes over the result. It had no notion of nesting,
of a component's slot, or of where the template ends — so it could only see
attributes ON the element, and an accessible name that comes from anywhere
else read as an absent one. Measured across 21 fleet repos: **1,211
findings, 58% of them false**, in four shapes:

  implicit label wrapping   `<label><input …><span>Safe mode</span></label>`
                            is the canonical HTML association and needs no
                            `for`/`id` pair at all. 268 findings.

  NcCheckboxRadioSwitch     `<NcCheckboxRadioSwitch v-model="x">Installed
  default slot              apps only</NcCheckboxRadioSwitch>` — nc-vue
                            renders the default slot INTO the `<label>`.
                            463 findings, and this is the dangerous one:
                            the only way to satisfy the old gate was to add
                            `aria-label`, which OVERRIDES the visible label
                            and breaks speech-input users who say what they
                            see. A gate whose remediation is an
                            accessibility REGRESSION cannot be closed
                            honestly.

  dynamic :id / :for        `<label :for="`f-${id}`">` + `<input
                            :id="`f-${id}`">` is a correct association the
                            literal-only regex could not see. 56 findings.

  commented-out markup      `<!-- <input type="text"> -->` ships nothing.
                            5 findings.

WHAT STILL FAILS, AND MUST
--------------------------
A control with no accessible name from ANY of the recognised sources is
still reported. Every relaxation here is anchored to a real naming
mechanism the browser implements — a wrapping `<label>`, a matching
`for`/`id` pair (literal or expression), a component prop the library
documents, or slot content the component renders into its own `<label>`.
An `<input type="text">` standing on its own, a self-closed
`<NcCheckboxRadioSwitch />` with no prop and no slot, and a `<label>` whose
`for` matches no control are all still findings. See
``test_check_form_labels.py``, where each relaxation ships with the
true-positive case it must not swallow.

Usage:
    check_form_labels.py <file.vue>...        # findings on stdout
"""
from __future__ import annotations

import re
import sys

# Native controls that need a name. `select` is deliberately absent: it is
# gate-12 (nc-input-labels)' subject, and widening this gate's remit while
# fixing its false-positive rate would make the two numbers incomparable.
NATIVE = {'input', 'textarea'}
# Nextcloud components whose published API takes the name as a prop.
# `NcSelect` belongs to gate-12, same reason.
NC_PROP_COMPONENTS = {'nctextfield', 'ncinputfield', 'ncrichcontenteditable',
                      'nccheckboxradioswitch'}
# ...of which these ALSO accept the name as default-slot content, because
# they render that slot inside their own <label> element.
NC_SLOT_COMPONENTS = {'nccheckboxradioswitch'}

# `type=` values that carry their own name or take none.
EXEMPT_INPUT_TYPES = {'hidden', 'submit', 'button', 'reset', 'image'}

TAG = re.compile(
    r'<(/?)([A-Za-z][A-Za-z0-9._:-]*)((?:"[^"]*"|\'[^\']*\'|[^>"\'])*?)(/?)>',
    re.DOTALL,
)
COMMENT = re.compile(r'<!--.*?-->', re.DOTALL)
BLOCK = re.compile(r'<(script|style)\b[^>]*>.*?</\1\s*>', re.DOTALL | re.IGNORECASE)
TEMPLATE = re.compile(r'<template\b[^>]*>(.*)</template\s*>', re.DOTALL | re.IGNORECASE)

ARIA = re.compile(r'(^|\s)(:|v-bind:)?(aria-label|aria-labelledby)\s*=')
NC_LABEL_PROP = re.compile(
    r'(^|\s)(:|v-bind:)?(label|input-label|inputLabel|aria-label-combobox|ariaLabelCombobox)\s*=')


def _attr(attrs: str, name: str) -> str | None:
    """Value of *name* (or its bound `:name` form) as written, or None."""
    m = re.search(
        r'(?:^|\s)(?::|v-bind:)?' + re.escape(name) + r'\s*=\s*("([^"]*)"|\'([^\']*)\')',
        attrs)
    if not m:
        return None
    return m.group(2) if m.group(2) is not None else m.group(3)


def _norm_expr(value: str) -> str:
    """Normalise a `for`/`id` value so a literal and a bound expression that
    denote the same thing compare equal. Whitespace-insensitive; quotes
    unified. `` `f-${id}` `` from a `:for` and from an `:id` match."""
    return re.sub(r'\s+', '', value).replace('"', "'")


def _strip_noise(src: str) -> str:
    """Template region only, comments and script/style blocks removed.

    Order matters: comments first, because a commented-out `</script>`
    would otherwise end the block early.
    """
    body = COMMENT.sub(' ', src)
    m = TEMPLATE.search(body)
    if m:
        body = m.group(1)
    return BLOCK.sub(' ', body)


class _El:
    __slots__ = ('name', 'attrs', 'start', 'text_start')

    def __init__(self, name: str, attrs: str, start: int, text_start: int):
        self.name = name
        self.attrs = attrs
        self.start = start
        self.text_start = text_start


def scan_source(fname: str, src: str) -> list[str]:
    """Return finding lines for one component source."""
    body = _strip_noise(src)

    # Pass 1 — every `for=` / `:for=` a <label> declares, normalised.
    label_for: set[str] = set()
    for m in TAG.finditer(body):
        closing, name, attrs, _self = m.group(1), m.group(2).lower(), m.group(3), m.group(4)
        if closing or name != 'label':
            continue
        v = _attr(attrs, 'for')
        if v:
            label_for.add(_norm_expr(v))

    findings: list[str] = []
    stack: list[_El] = []
    label_depth = 0

    def _named_by_attrs(name: str, attrs: str) -> bool:
        if ARIA.search(attrs):
            return True
        if name in NC_PROP_COMPONENTS and NC_LABEL_PROP.search(attrs):
            return True
        if name in NATIVE:
            v = _attr(attrs, 'id')
            if v and _norm_expr(v) in label_for:
                return True
        return False

    def _report(name: str, attrs: str, rule: str) -> None:
        rendered = re.sub(r'\s+', ' ', f'<{name}{attrs}>').strip()
        if len(rendered) > 200:
            rendered = rendered[:197] + '...'
        findings.append(f'{fname}: {rendered} rule={rule}')

    for m in TAG.finditer(body):
        closing, raw_name, attrs, self_close = m.group(1), m.group(2), m.group(3), m.group(4)
        name = raw_name.lower()
        void = name in {'input', 'img', 'br', 'hr', 'meta', 'link', 'source', 'area'}

        if closing:
            # Pop back to the matching open tag, tolerating unbalanced markup.
            for i in range(len(stack) - 1, -1, -1):
                if stack[i].name == name:
                    el = stack[i]
                    inner = body[el.text_start:m.start()]
                    if el.name in NC_SLOT_COMPONENTS:
                        _decide_slot_component(el, inner, _report)
                    del stack[i:]
                    break
            label_depth = sum(1 for e in stack if e.name == 'label')
            continue

        is_void = void or bool(self_close)

        if name == 'input':
            t = (_attr(attrs, 'type') or 'text').strip().lower()
            if t not in EXEMPT_INPUT_TYPES:
                if not (_named_by_attrs(name, attrs) or label_depth > 0):
                    _report(raw_name, attrs, 'input-without-label')
        elif name == 'textarea':
            if not (_named_by_attrs(name, attrs) or label_depth > 0):
                _report(raw_name, attrs, f'{name}-without-label')
        elif name in NC_PROP_COMPONENTS:
            named = _named_by_attrs(name, attrs) or label_depth > 0
            if named:
                pass
            elif name in NC_SLOT_COMPONENTS and not is_void:
                # Defer: the default slot may supply the label. Decided when
                # the closing tag is reached.
                pass
            else:
                _report(raw_name, attrs, f'{name}-without-label-prop')

        if not is_void:
            stack.append(_El(name, attrs, m.start(), m.end()))
            if name == 'label':
                label_depth += 1

    # Unclosed slot components: no closing tag was ever seen, so no slot
    # content was proved. Report rather than silently accept.
    for el in stack:
        if el.name in NC_SLOT_COMPONENTS and not (
                ARIA.search(el.attrs) or NC_LABEL_PROP.search(el.attrs)):
            _report(el.name, el.attrs, f'{el.name}-without-label-prop')

    return findings


def _decide_slot_component(el: _El, inner: str, report) -> None:
    """A slot-labelling component is named iff its default slot renders
    something. Whitespace, and nothing else, is not a name."""
    if ARIA.search(el.attrs) or NC_LABEL_PROP.search(el.attrs):
        return
    # Strip nested tags; what remains is the text the user would read. A
    # `{{ t('app', 'Installed apps only') }}` interpolation counts — it is
    # the translated visible label.
    text = TAG.sub(' ', inner)
    if text.strip():
        return
    report(el.name, el.attrs, f'{el.name}-without-label-prop')


def scan_files(files: list[str]) -> list[str]:
    out: list[str] = []
    for fname in files:
        try:
            with open(fname, encoding='utf-8', errors='replace') as f:
                src = f.read()
        except OSError:
            continue
        out.extend(scan_source(fname, src))
    return out


def main(argv: list[str]) -> int:
    for line in scan_files(argv[1:]):
        print(line)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
