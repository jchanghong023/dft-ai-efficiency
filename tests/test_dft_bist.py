"""Pure-model checks for the offline MBIST/BIRA/BISR and LBIST labs."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
JS = ROOT / "portal/assets/labs/bist.js"
NODE = shutil.which("node")


@unittest.skipUnless(NODE, "Node.js is required for the pure JavaScript model checks")
class BistModelTests(unittest.TestCase):
    def run_node(self, expression: str) -> dict:
        script = (
            "const fs=require('fs');"
            f"eval(fs.readFileSync({json.dumps(str(JS))}, 'utf8'));"
            f"console.log(JSON.stringify({expression}));"
        )
        result = subprocess.run(
            [NODE, "-e", script], cwd=ROOT, check=True, text=True,
            capture_output=True, env={**os.environ, "NODE_NO_WARNINGS": "1"},
        )
        return json.loads(result.stdout)

    def test_memory_march_detects_and_repairs_one_row(self):
        value = self.run_node(
            "(()=>{const m=DFTLabModels.bistMemory.create({fault:'stuck1'});"
            "while(m.state.phase==='test')m.step();"
            "const failures=[...new Set(m.state.failures.map(x=>x.address))];"
            "const allocation=m.analyze();m.applyRepair();"
            "while(m.state.phase==='verify')m.step();"
            "return {failures,allocation,result:m.state.result,verification:m.state.verificationFailures};})()"
        )
        self.assertEqual(value["failures"], [3])
        self.assertEqual(value["allocation"]["mapping"], {"3": 8})
        self.assertEqual(value["allocation"]["unrepairable"], [])
        self.assertEqual(value["result"], "pass")
        self.assertEqual(value["verification"], [])

    def test_bira_reports_spare_exhaustion_instead_of_claiming_pass(self):
        value = self.run_node(
            "(()=>{const m=DFTLabModels.bistMemory.create({fault:'two'});"
            "while(m.state.phase==='test')m.step();const allocation=m.analyze();m.applyRepair();"
            "while(m.state.phase==='verify')m.step();"
            "return {allocation,result:m.state.result,remaining:m.state.verificationFailures.map(x=>x.address)};})()"
        )
        self.assertEqual(value["allocation"]["mapping"], {"3": 8})
        self.assertEqual(value["allocation"]["unrepairable"], [6])
        self.assertEqual(value["result"], "fail")
        self.assertIn(6, value["remaining"])

    def test_lbist_known_sequence_signature_and_fault(self):
        value = self.run_node(
            "(()=>{const good=DFTLabModels.bistLogic.create();"
            "while(good.state.phase!=='done')good.step();"
            "const bad=DFTLabModels.bistLogic.create();"
            "while(bad.state.phase!=='done')bad.step('stuck');"
            "return {sequence:DFTLabModels.bistLogic.knownSequence,signature:good.state.signature,"
            "expected:good.state.expected,goodResult:good.state.result,badSignature:bad.state.signature,badResult:bad.state.result};})()"
        )
        self.assertEqual(value["sequence"], [1, 2, 4, 9, 3, 6, 13, 10])
        self.assertEqual(value["signature"], 8)
        self.assertEqual(value["signature"], value["expected"])
        self.assertEqual(value["goodResult"], "pass")
        self.assertNotEqual(value["badSignature"], value["expected"])
        self.assertEqual(value["badResult"], "fail")

        vector = self.run_node(
            "({responses:DFTLabModels.bistLogic.knownResponses,signatures:DFTLabModels.bistLogic.knownSignatures,"
            "singleInputOne:DFTLabModels.bistLogic.misrStep(0,1)})"
        )
        self.assertEqual(vector["responses"], [3, 7, 14, 15, 4, 9, 1, 11])
        self.assertEqual(vector["signatures"], [7, 8, 2, 4, 10, 5, 4, 8])
        self.assertEqual(vector["singleInputOne"], 11)

    def test_non_positive_cycle_count_falls_back_to_known_length(self):
        value = self.run_node(
            "(()=>{const m=DFTLabModels.bistLogic.create({cycles:0});"
            "while(m.state.phase!=='done')m.step();"
            "return {cycles:m.state.cycles,result:m.state.result};})()"
        )
        self.assertEqual(value, {"cycles": 8, "result": "pass"})

    def test_node_load_has_no_dom_requirement(self):
        value = self.run_node(
            "({memory:typeof DFTLabModels.bistMemory.create,logic:typeof DFTLabModels.bistLogic.create,document:typeof document})"
        )
        self.assertEqual(value, {"memory": "function", "logic": "function", "document": "undefined"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
