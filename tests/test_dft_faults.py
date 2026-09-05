"""Pure-model checks for the fault, coverage, and test-point DFT labs."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "portal" / "assets" / "labs" / "faults.js"


def call_model(expression: str):
    script = f"require({json.dumps(str(MODEL))}); console.log(JSON.stringify({expression}));"
    result = subprocess.run(["node", "-e", script], cwd=ROOT, capture_output=True, text=True, encoding="utf-8", check=True)
    return json.loads(result.stdout)


class FaultLabModelTests(unittest.TestCase):
    def test_stuck_at_can_be_activated_and_observed(self):
        result = call_model("DFTLabModels.faults.simulate({fault:'stuck-at-0', pattern:'10'})")
        self.assertEqual(result["good"]["out"], 1)
        self.assertTrue(result["activated"])
        self.assertTrue(result["detected"])
        self.assertEqual(result["result"], "detected")

    def test_stimulus_can_fail_to_activate_fault(self):
        result = call_model("DFTLabModels.faults.simulate({fault:'stuck-at-0', pattern:'00'})")
        self.assertFalse(result["activated"])
        self.assertFalse(result["detected"])

    def test_invalid_pattern_is_normalized_to_zeroes(self):
        result = call_model("DFTLabModels.faults.simulate({fault:'stuck-at-0', pattern:'not-bits'})")
        self.assertEqual(result["good"]["a"], 0)
        self.assertEqual(result["good"]["b"], 0)

    def test_transition_model_uses_previous_and_current_values(self):
        result = call_model("DFTLabModels.faults.simulate({fault:'transition-rise', pattern:'10', previous:'00'})")
        self.assertTrue(result["activated"])
        self.assertEqual(result["faulty"]["out"], 0)
        self.assertTrue(result["detected"])

    def test_coverage_keeps_aborted_in_second_denominator(self):
        all_items = call_model("DFTLabModels.faults.coverageSummary(undefined, 'all')")
        excluding = call_model("DFTLabModels.faults.coverageSummary(undefined, 'excluding-untestable')")
        self.assertEqual(all_items["total"], 20)
        self.assertEqual(all_items["denominator"], 20)
        self.assertEqual(all_items["percentage"], 60)
        self.assertEqual(excluding["denominator"], 18)
        self.assertEqual(excluding["percentage"], 66.7)
        empty = call_model("DFTLabModels.faults.coverageSummary({detected:0,'not-detected':0,untestable:0,aborted:0}, 'all')")
        self.assertIsNone(empty["percentage"])
        self.assertFalse(empty["applicable"])

    def test_test_points_enumerate_concrete_fault_differences(self):
        baseline = call_model("DFTLabModels.faults.testPointImpact('none')")
        control = call_model("DFTLabModels.faults.testPointImpact('control')")
        observe = call_model("DFTLabModels.faults.testPointImpact('observe')")
        both = call_model("DFTLabModels.faults.testPointImpact('both')")
        self.assertEqual(baseline["detectedFaults"], [])
        self.assertEqual(control["detectedFaults"], ["h-stuck-at-0", "p-stuck-at-0"])
        self.assertEqual(observe["detectedFaults"], ["h-stuck-at-0"])
        self.assertEqual(both["detectedFaults"], ["h-stuck-at-0", "p-stuck-at-0"])
        self.assertEqual(control["detectedByFault"]["p-stuck-at-0"], ["01", "10"])
        self.assertEqual(observe["detectedByFault"]["h-stuck-at-0"], ["11"])
        self.assertNotEqual(baseline["activationByFault"]["h-stuck-at-0"], control["activationByFault"]["h-stuck-at-0"])
        for data in (baseline, control, observe, both):
            for fault in data["faults"]:
                self.assertTrue(set(data["detectedByFault"][fault]).issubset(set(data["activationByFault"][fault])))
        self.assertNotIn("00", both["detectedByFault"]["p-stuck-at-0"])
        self.assertEqual(both["patternCount"], 4)


if __name__ == "__main__":
    unittest.main(verbosity=2)
