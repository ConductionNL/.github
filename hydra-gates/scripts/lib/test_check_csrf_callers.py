#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Tests for check_csrf_callers (gate-48 companion).

Run with:  python3 scripts/lib/test_check_csrf_callers.py

Both arms, per #191's rule: arm 2 is the one that proves the companion did not
simply declare every repository compliant. A checker that reports nothing looks
exactly like a codebase with nothing to report.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_csrf_callers as gate  # noqa: E402


def app_with(files: dict[str, str]) -> str:
    """Materialise a throwaway app dir; returns its path."""
    root = tempfile.mkdtemp()
    for rel, content in files.items():
        path = os.path.join(root, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(content)
    return root


class TestCompliantCallersReportNothing(unittest.TestCase):
    """Arm 1 — the larpingapp#298 shape: every caller already sends a token."""

    def test_the_larpingapp_settings_store(self):
        root = app_with({'src/store/modules/settings.js': """
export default {
    async saveSettings(config) {
        const response = await fetch('/apps/larpingapp/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                requesttoken: OC.requestToken,
            },
            body: JSON.stringify(config),
        })
        return response.json()
    },
}
"""})
        self.assertEqual(gate.unprotected_call_sites(root), [])

    def test_an_ocs_apirequest_header_counts(self):
        root = app_with({'src/x.vue': """
await fetch(url, { method: 'POST', headers: { 'OCS-APIREQUEST': 'true' } })
"""})
        self.assertEqual(gate.unprotected_call_sites(root), [])

    def test_get_request_token_counts(self):
        root = app_with({'src/x.js': """
await fetch(url, { method: 'PUT', headers: { requesttoken: getRequestToken() } })
"""})
        self.assertEqual(gate.unprotected_call_sites(root), [])

    def test_nextcloud_axios_injects_the_token(self):
        root = app_with({'src/x.js': """
import axios from '@nextcloud/axios'
export const save = () => axios.post('/apps/x/api/settings', {})
"""})
        self.assertEqual(gate.unprotected_call_sites(root), [])

    def test_a_plain_GET_fetch_is_not_a_mutating_call(self):
        root = app_with({'src/x.js': "const r = await fetch('/apps/x/api/settings')\n"})
        self.assertEqual(gate.unprotected_call_sites(root), [])

    def test_an_app_with_no_src_directory(self):
        self.assertEqual(gate.unprotected_call_sites(app_with({'lib/X.php': '<?php'})), [])


class TestUnprotectedCallersAreReported(unittest.TestCase):
    """Arm 2 — the gate must still catch what it was built for."""

    def test_the_opencatalogi_79_delete_modal(self):
        """The defect gate-48 exists for: a delete-modal fetch() with no CSRF
        header. If this stopped being reported the gate would be switched off."""
        root = app_with({'src/modals/DeleteModal.vue': """
export default {
    methods: {
        async destroy(id) {
            await fetch(`/apps/opencatalogi/api/publications/${id}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
            })
        },
    },
}
"""})
        found = gate.unprotected_call_sites(root)
        self.assertEqual(len(found), 1, found)
        self.assertIn('src/modals/DeleteModal.vue', found[0])
        self.assertIn('DELETE', found[0])

    def test_a_bare_axios_post_without_the_nextcloud_wrapper(self):
        root = app_with({'src/x.js': """
import axios from 'axios'
export const save = () => axios.post('/apps/x/api/settings', {})
"""})
        found = gate.unprotected_call_sites(root)
        self.assertEqual(len(found), 1, found)
        self.assertIn('axios.post()', found[0])

    def test_every_mutating_verb_is_covered(self):
        for verb in ('POST', 'PUT', 'PATCH', 'DELETE'):
            root = app_with({'src/x.js': f"await fetch(u, {{ method: '{verb}' }})\n"})
            found = gate.unprotected_call_sites(root)
            self.assertEqual(len(found), 1, f"{verb}: {found}")
            self.assertIn(verb, found[0])

    def test_a_token_on_a_DIFFERENT_call_does_not_protect_this_one(self):
        """Paren-balanced extraction. A file-wide search would let one correct
        call vouch for every incorrect one beside it."""
        root = app_with({'src/x.js': """
await fetch(a, { method: 'POST', headers: { requesttoken: OC.requestToken } })
await fetch(b, { method: 'POST', headers: { 'Content-Type': 'application/json' } })
"""})
        found = gate.unprotected_call_sites(root)
        self.assertEqual(len(found), 1, found)
        self.assertIn(':3', found[0])

    def test_node_modules_is_not_scanned(self):
        root = app_with({
            'src/node_modules/dep/index.js': "fetch(u, { method: 'POST' })\n",
            'src/ok.js': "fetch(u, { method: 'POST', headers: { requesttoken: t } })\n",
        })
        self.assertEqual(gate.unprotected_call_sites(root), [])

    def test_the_reported_line_number_is_the_call(self):
        root = app_with({'src/x.js': "\n\n\nawait fetch(u, { method: 'POST' })\n"})
        found = gate.unprotected_call_sites(root)
        self.assertEqual(len(found), 1, found)
        self.assertIn('src/x.js:4', found[0])


class TestCli(unittest.TestCase):
    def test_missing_argument_is_rejected(self):
        self.assertEqual(gate.main(["check_csrf_callers.py"]), 2)

    def test_extra_arguments_are_rejected(self):
        self.assertEqual(gate.main(["check_csrf_callers.py", "a", "b"]), 2)


class TestACommentIsNotACsrfToken(unittest.TestCase):
    """A comment is not a token (#415).

    THIS HELPER MAKES AN AFFIRMATIVE CLAIM, which is why prose here is worse
    than elsewhere in the class. When it returns nothing the runner prints

        [gate-48] NOTE: no CSRF signal was ADDED by this diff, and none was
        needed: every mutating call site under src/ already carries one …

    and passes. So a comment did not merely hide a finding — it manufactured
    a green WITH A SENTENCE ATTACHED SAYING THE CODE IS SAFE.

    Every arm below is paired with the real mechanism it must not swallow,
    because `script_mask` keeps string literals ON PURPOSE: `'OCS-APIRequest'`
    is a header name that IS a string, and `method: 'DELETE'` is how a
    mutating call is recognised at all. A mask that blanked literals would
    pass every closure arm here and turn the gate off completely.
    """

    _UNPROTECTED = """<script>
export default { methods: { async del(id) {
%s  await fetch(`/api/things/${id}`, { method: 'DELETE',%s headers: {} })
} } }
</script>
"""

    def test_positive_control_an_unprotected_fetch_is_reported(self):
        root = app_with({'src/components/Del.vue': self._UNPROTECTED % ('', '')})
        found = gate.unprotected_call_sites(root)
        self.assertEqual(len(found), 1, found)
        self.assertIn('fetch()', found[0])

    def test_a_todo_above_the_call_is_not_the_header(self):
        """CONTROL, not evidence — it passes with the mask and without it.

        The comment sits ABOVE the call, outside the paren-balanced span
        `CSRF_SIGNAL` is searched against, so it never reached the question.
        Kept because it pins the boundary: the arm below is the same sentence
        moved three characters into the span, and that one flips."""
        root = app_with({'src/components/Del.vue': self._UNPROTECTED % (
            '  // TODO: add the requesttoken header here. Not done yet.\n', '')})
        found = gate.unprotected_call_sites(root)
        self.assertEqual(len(found), 1, found)

    def test_a_todo_inside_the_init_object_is_not_the_header(self):
        """EVIDENCE — flips when the mask is removed.

        The comment sits INSIDE the paren-balanced call text, which is the
        span `CSRF_SIGNAL` is actually searched against. Without the mask this
        call is reported protected and the runner prints the NOTE."""
        root = app_with({'src/components/Del.vue': self._UNPROTECTED % (
            '', '\n    // TODO: requesttoken goes here once #999 lands.')})
        found = gate.unprotected_call_sites(root)
        self.assertEqual(len(found), 1, found)

    def test_a_real_header_is_still_protection(self):
        """The pair. `requesttoken` as an object key and `'OCS-APIRequest'` as
        a string value must both survive the mask."""
        root = app_with({'src/components/Del.vue': """<script>
export default { methods: { async del(id) {
  await fetch(`/api/things/${id}`, { method: 'DELETE',
    headers: { requesttoken: OC.requestToken, 'OCS-APIRequest': 'true' } })
} } }
</script>
"""})
        self.assertEqual(gate.unprotected_call_sites(root), [])

    def test_a_commented_out_nextcloud_axios_import_grants_no_amnesty(self):
        """EVIDENCE — flips when the mask is removed.

        `NEXTCLOUD_AXIOS_IMPORT` was read raw too, and it is a WHOLE-FILE
        switch: one dead import line silenced every axios.post in the file at
        once."""
        root = app_with({'src/components/Ax.vue': """<script>
// import axios from '@nextcloud/axios'
import axios from 'axios'
export default { methods: { async save(d) { await axios.post('/api/things', d) } } }
</script>
"""})
        found = gate.unprotected_call_sites(root)
        self.assertEqual(len(found), 1, found)
        self.assertIn('axios.post()', found[0])

    def test_a_real_nextcloud_axios_import_still_protects_the_file(self):
        """The pair for the arm above."""
        root = app_with({'src/components/Ax.vue': """<script>
import axios from '@nextcloud/axios'
export default { methods: { async save(d) { await axios.post('/api/things', d) } } }
</script>
"""})
        self.assertEqual(gate.unprotected_call_sites(root), [])

    def test_the_reported_line_number_still_addresses_the_original_file(self):
        """The mask is length-preserving, so masking must not shift the line a
        finding names. A finding that points at the wrong line is how a real
        one gets dismissed as noise."""
        root = app_with({'src/components/Del.vue': (
            "<script>\n// filler\n// filler\n// filler\n"
            "export default { methods: { async del(id) {\n"
            "  await fetch(`/api/x`, { method: 'DELETE', headers: {} })\n"
            "} } }\n</script>\n")})
        found = gate.unprotected_call_sites(root)
        self.assertEqual(len(found), 1, found)
        self.assertIn(':6', found[0])


if __name__ == "__main__":
    unittest.main()
