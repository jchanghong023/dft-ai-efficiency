"""Pure API checks for the standalone compression and test-power labs."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "portal" / "assets" / "labs" / "compression-power.js"


def node_json(expression: str) -> dict:
    code = f"require({json.dumps(str(SCRIPT))}); console.log(JSON.stringify({expression}));"
    completed = subprocess.run(["node", "-e", code], cwd=ROOT, text=True, encoding="utf-8", capture_output=True, check=True)
    return json.loads(completed.stdout.strip())


class CompressionPowerLabTests(unittest.TestCase):
    def test_models_are_available_without_dom(self):
        result = node_json("Object.keys(globalThis.DFTLabModels).sort()")
        self.assertEqual(result, ["compression", "power"])

    def test_compression_care_mask_and_x_propagation(self):
        result = node_json("globalThis.DFTLabModels.compression.evaluate({care:'10?1', response:'1011', mask:'0010'})")
        self.assertTrue(result["solvable"])
        self.assertEqual([item["inputs"] for item in result["matches"]], [[1, 0]])
        self.assertEqual(result["chainStimulus"], ["1", "0", "1", "1"])
        self.assertEqual(result["observed"], ["1", "0", "M", "1"])
        self.assertEqual(result["output"], ["1", "1"])
        propagated = node_json("globalThis.DFTLabModels.compression.evaluate({care:'10?1', response:'1X11', mask:'0000'})")
        self.assertEqual(propagated["output"], ["0", "X"])
        bypassed = node_json("globalThis.DFTLabModels.compression.evaluate({care:'10?1', response:'1011', mask:'0010', bypass:true})")
        self.assertEqual(bypassed["output"], ["1", "0", "M", "1"])
        impossible = node_json("globalThis.DFTLabModels.compression.evaluate({care:'0010', response:'1011', mask:'0000'})")
        self.assertFalse(impossible["solvable"])
        invalid = node_json("globalThis.DFTLabModels.compression.evaluate({care:'10a1', response:'1011', mask:'0010'})")
        self.assertFalse(invalid["valid"])

    def test_power_shift_capture_and_staggering(self):
        parallel = node_json("globalThis.DFTLabModels.power.evaluate({shift:'10110011', capture:'110010100011', activeDomains:[true,true,true], schedule:'parallel', isolation:true})")
        self.assertEqual(parallel["shiftFlips"], 18)
        self.assertEqual(parallel["captureFlips"], 6)
        self.assertEqual(parallel["peakConcurrentFlips"], 6)
        self.assertEqual(parallel["captureByDomain"], [2, 2, 2])
        staggered = node_json("globalThis.DFTLabModels.power.evaluate({shift:'10110011', capture:'110010100011', activeDomains:[true,false,true], schedule:'staggered', isolation:true})")
        self.assertEqual(staggered["captureByDomain"], [2, 0, 2])
        self.assertEqual(staggered["peakConcurrentFlips"], 2)
        self.assertEqual(staggered["boundary"], ["0", "0", "1"])
        no_isolation = node_json("globalThis.DFTLabModels.power.evaluate({shift:'10110011', capture:'110010100011', activeDomains:[true,false,true], schedule:'staggered', isolation:false})")
        self.assertEqual(no_isolation["boundary"], ["0", "X", "1"])
        invalid = node_json("globalThis.DFTLabModels.power.evaluate({shift:'1012', capture:'110010100011'})")
        self.assertFalse(invalid["valid"])

    def test_capture_has_exactly_three_domains_and_zero_states_do_not_toggle(self):
        for capture in ("1010", "1" * 13):
            result = node_json(f"globalThis.DFTLabModels.power.evaluate({{capture:{json.dumps(capture)}}})")
            self.assertFalse(result["valid"])
        quiet = node_json("globalThis.DFTLabModels.power.evaluate({shift:'0000',capture:'000000000000'})")
        self.assertEqual((quiet["shiftFlips"], quiet["captureFlips"], quiet["peakConcurrentFlips"]), (0, 0, 0))
        self.assertEqual(quiet["boundary"], ["0", "0", "0"])

    def test_documents_and_templates_are_offline_and_static_fallbacks_exist(self):
        compression = (ROOT / "portal" / "content" / "dft-compression.md").read_text(encoding="utf-8")
        power = (ROOT / "portal" / "content" / "dft-test-power.md").read_text(encoding="utf-8")
        self.assertIn("<!-- lab:compression -->", compression)
        self.assertIn("<!-- lab:test-power -->", power)
        self.assertGreaterEqual(len(compression.splitlines()), 60)
        self.assertGreaterEqual(len(power.splitlines()), 60)
        for name in ("compression.html", "test-power.html"):
            html = (ROOT / "portal" / "templates" / "labs" / name).read_text(encoding="utf-8")
            self.assertIn('class="lab-header"', html)
            self.assertIn('class="lab-controls"', html)
            self.assertIn('class="lab-stage"', html)
            self.assertIn('class="lab-readouts"', html)
            self.assertIn('class="lab-explanation"', html)
            self.assertIn("<noscript>", html)
            self.assertIn("disabled", html)
            self.assertNotRegex(html, r"https?://|fetch\s*\(")
        js = SCRIPT.read_text(encoding="utf-8")
        self.assertNotRegex(js, r"https?://|fetch\s*\(")
        self.assertIn('if (typeof document === "undefined") return;', js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
