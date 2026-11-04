#!/usr/bin/env python3
# SPDX-License-Identifier: EUPL-1.2
"""Every shipped OpenRegister contract is named where a consumer looks for it.

Gate 67 keeps hydra-gates/contracts/ byte-identical with openregister's
lib/Contract/. A consumer wires the files in by hand from the README: the
table of shipped contracts, the test-bootstrap guard and the Psalm stubs. A
file shipped in contracts/ but missing there is shipped and still unusable,
which is how EmailLinkReaderInterface went unlisted after it landed.
"""
import os
import unittest

PKG = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONTRACTS = os.path.join(PKG, "contracts")


class ShippedContractsDocumented(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(PKG, "README.md"), encoding="utf-8") as fh:
            self.readme = fh.read()
        self.files = sorted(f for f in os.listdir(CONTRACTS) if f.endswith(".php"))

    def test_the_contract_directory_is_not_empty(self):
        self.assertIn("EmailLinkReaderInterface.php", self.files)
        self.assertGreaterEqual(len(self.files), 5)

    def test_every_contract_has_a_row_in_the_table(self):
        for f in self.files:
            self.assertIn(f"| `{f}` |", self.readme, f"{f} has no row in the README contracts table")

    def test_every_contract_is_in_the_bootstrap_guard(self):
        for f in self.files:
            self.assertIn(f"'{f[:-4]}'", self.readme, f"{f} is missing from the README bootstrap guard")

    def test_every_contract_is_a_psalm_stub(self):
        for f in self.files:
            self.assertIn(f"hydra-gates/contracts/{f}\" />", self.readme, f"{f} is missing from the README Psalm stubs")


if __name__ == "__main__":
    unittest.main()
