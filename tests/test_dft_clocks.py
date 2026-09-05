"""Node-backed checks for the three deterministic DFT clock/scan lab models."""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")
JS = ROOT / "portal/assets/labs/clocks.js"


def run_node(expression: str):
    if NODE is None:
        raise unittest.SkipTest("node executable is unavailable")
    script = "const fs=require('fs');const vm=require('vm');vm.runInThisContext(fs.readFileSync(process.argv[1],'utf8'));" + expression
    completed = subprocess.run([str(NODE), "-e", script, str(JS)], cwd=ROOT,
                               capture_output=True, text=True, encoding='utf-8', check=True)
    return json.loads(completed.stdout)


class DftClockLabTests(unittest.TestCase):
    def test_occ_counts_source_edges_and_closes_capture_after_two_outputs(self):
        rows=run_node("console.log(JSON.stringify(['shift','capture'].map(mode=>{const m=DFTLabModels.clocksOcc.create({mode,scanEnable:mode==='shift',functionalClock:true});for(let i=0;i<4;i++)m.step();return {state:m.snapshot(),history:m.getHistory()};}))); ")
        self.assertEqual([e['outputEdges'] for e in rows[0]['history']],[0,1,2,3,4])
        self.assertEqual([e['outputEdges'] for e in rows[1]['history']],[0,1,2,2,2])
        self.assertEqual([e['pulse'] for e in rows[1]['history']],[None,'launch','capture',None,None])
        self.assertEqual([e['passed'] for e in rows[1]['history']],[False,True,True,False,False])
        self.assertTrue(all(row['state']['done'] for row in rows))

    def test_occ_all_boolean_control_combinations(self):
        rows=run_node("const rows=[];for(const mode of ['shift','capture'])for(const scanEnable of [true,false])for(const testEnable of [true,false])for(const resetAsserted of [true,false])for(const functionalClock of [true,false])rows.push(DFTLabModels.clocksOcc.run({mode,scanEnable,testEnable,resetAsserted,functionalClock}));console.log(JSON.stringify(rows));")
        self.assertEqual(len(rows),32)
        for row in rows:
            allowed=row['testEnable'] and not row['resetAsserted']
            if row['mode']=='shift':expected=4 if allowed and row['scanEnable'] else 0
            else:expected=2 if allowed and not row['scanEnable'] and row['functionalClock'] else 0
            self.assertEqual(row['outputEdges'],expected)
            self.assertEqual(sum(e['passed'] for e in row['events']),expected)
            self.assertEqual(row['availableEdges'],4 if row['mode']=='shift' or row['functionalClock'] else 0)

    def test_occ_missing_source_partial_capture_invalid_count_and_reset(self):
        result=run_node("const o={mode:'capture',scanEnable:false,functionalClock:true};const m=DFTLabModels.clocksOcc.create(o);m.step();const h=m.getHistory();h[1].outputEdges=999;const intact=m.snapshot();m.reset(o);console.log(JSON.stringify({empty:DFTLabModels.clocksOcc.run({...o,functionalEdges:0}),partial:DFTLabModels.clocksOcc.run({...o,functionalEdges:1}),invalid:DFTLabModels.clocksOcc.run({...o,functionalEdges:2.5}),intact,reset:m.snapshot(),history:m.getHistory()}));")
        self.assertEqual(result['empty']['pulses'],[])
        self.assertFalse(result['empty']['requestComplete'])
        self.assertEqual(result['partial']['pulses'],['launch'])
        self.assertFalse(result['partial']['requestComplete'])
        self.assertFalse(result['invalid']['valid'])
        self.assertEqual(result['invalid']['pulses'],[])
        self.assertEqual(result['intact']['outputEdges'],1)
        self.assertEqual(result['reset']['outputEdges'],0)
        self.assertEqual(len(result['history']),1)

    def test_at_speed_loc_los_and_margin_calculation(self):
        result = run_node("console.log(JSON.stringify({loc:DFTLabModels.clocksAtSpeed.run({mode:'LOC',pathDelayNs:6.5,periodNs:10}),los:DFTLabModels.clocksAtSpeed.run({mode:'LOS',pathDelayNs:9.8,periodNs:10})}));")
        self.assertEqual([event['name'] for event in result['loc']['events']], ['shift', 'launch', 'capture'])
        self.assertEqual(result['loc']['arrivalNs'], 6.9)
        self.assertEqual(result['loc']['requiredNs'], 9.5)
        self.assertTrue(result['loc']['pass'])
        self.assertEqual([event['name'] for event in result['los']['events']], ['shift-launch', 'se-low', 'capture'])
        self.assertEqual(result['los']['slackNs'], -0.7)
        self.assertFalse(result['los']['pass'])

    def test_invalid_at_speed_and_los_switch_timing_are_rejected(self):
        result = run_node("console.log(JSON.stringify({bad:DFTLabModels.clocksAtSpeed.run({mode:'LOS',periodNs:0.1,seLowNs:0.2}),invalid:DFTLabModels.clocksAtSpeed.run({mode:'BAD',pathDelayNs:'x'})}));")
        self.assertFalse(result['bad']['valid'])
        self.assertFalse(result['bad']['seSafe'])
        self.assertFalse(result['invalid']['valid'])
        self.assertTrue(result['invalid']['errors'])

    def test_occ_respects_mode_enable_and_reset(self):
        result = run_node("console.log(JSON.stringify({shift:DFTLabModels.clocksOcc.run({mode:'shift',scanEnable:true,testEnable:true,externalEdges:4}),capture:DFTLabModels.clocksOcc.run({mode:'capture',functionalClock:true,scanEnable:false,testEnable:true}),blocked:DFTLabModels.clocksOcc.run({mode:'capture',functionalClock:true,testEnable:true,resetAsserted:true})}));")
        self.assertEqual(result['shift']['pulses'], ['shift'] * 4)
        self.assertEqual(result['capture']['pulses'], ['launch', 'capture'])
        blocked_capture = run_node("console.log(JSON.stringify(DFTLabModels.clocksOcc.run({mode:'capture',functionalClock:true,scanEnable:true,testEnable:true}))); ")
        self.assertEqual(blocked_capture['pulses'], [])
        self.assertEqual(result['blocked']['outputEdges'], 0)
        self.assertIn('复位', result['blocked']['reason'])

    def test_scan_balance_and_lockup_change_hold_result(self):
        result = run_node("console.log(JSON.stringify({balance:DFTLabModels.clocksScanEngineering.balance([8,8,7,9]),without:DFTLabModels.clocksScanEngineering.timing({destinationEdgeNs:0.3,holdWindowNs:0.5,lockup:false}),with:DFTLabModels.clocksScanEngineering.timing({destinationEdgeNs:0.3,holdWindowNs:0.5,lockup:true})}));")
        self.assertEqual(result['balance']['shiftCycles'], 9)
        self.assertEqual(result['balance']['spread'], 2)
        self.assertFalse(result['balance']['balanced'])
        self.assertEqual(result['without']['holdMarginNs'], -0.6)
        self.assertEqual(result['with']['holdMarginNs'], 4.4)
        self.assertFalse(result['without']['safe'])
        self.assertTrue(result['with']['safe'])
        later = run_node("console.log(JSON.stringify(DFTLabModels.clocksScanEngineering.timing({destinationEdgeNs:0.6,holdWindowNs:0.5,lockup:false}))); ")
        self.assertLess(later['holdMarginNs'], result['without']['holdMarginNs'])

    def test_invalid_scan_lengths_and_timing_are_rejected(self):
        result = run_node("console.log(JSON.stringify({lengths:DFTLabModels.clocksScanEngineering.balance(['8','x',0]),timing:DFTLabModels.clocksScanEngineering.timing({destinationEdgeNs:'x',holdWindowNs:-1})}));")
        self.assertFalse(result['lengths']['valid'])
        self.assertFalse(result['lengths']['balanced'])
        self.assertFalse(result['timing']['valid'])
        self.assertFalse(result['timing']['safe'])

    def test_pages_and_markers_are_present(self):
        expected = {
            'dft-at-speed.md': 'lab:at-speed',
            'dft-clock-reset.md': 'lab:clock-reset',
            'dft-scan-engineering.md': 'lab:scan-engineering',
        }
        for filename, marker in expected.items():
            text = (ROOT / 'portal/content' / filename).read_text(encoding='utf-8')
            self.assertIn('<!-- ' + marker + ' -->', text)
            self.assertGreaterEqual(len(text.splitlines()), 60)
        for filename in ('at-speed.html', 'clock-reset.html', 'scan-engineering.html'):
            self.assertTrue((ROOT / 'portal/templates/labs' / filename).exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
