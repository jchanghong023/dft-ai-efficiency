"""Pure Node model checks for the offline DFT engineering-flow lab."""
from __future__ import annotations
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "portal/assets/labs/flow.js"
TEMPLATE = ROOT / "portal/templates/labs/flow.html"


def node_json(expression: str):
    script = f"const fs=require('fs'),vm=require('vm'); const g={{console}}; vm.createContext(g); vm.runInContext(fs.readFileSync({json.dumps(str(MODEL))},'utf8'),g); process.stdout.write(JSON.stringify({expression}));"
    completed = subprocess.run(["node", "-e", script], cwd=ROOT, check=True, capture_output=True, text=True,
                               encoding="utf-8")
    return json.loads(completed.stdout)


class DftFlowModelTests(unittest.TestCase):
    def test_static_lab_starts_safe_and_exposes_explanation_binding(self):
        source = TEMPLATE.read_text(encoding="utf-8")
        self.assertIn('data-setting="symptom" disabled', source)
        self.assertIn('data-action="inspect" disabled', source)
        self.assertIn('data-action="next" disabled', source)
        self.assertIn('data-action="reset" disabled', source)
        self.assertIn('data-field="explanation"', source)

    def test_all_symptoms_require_their_own_evidence_before_progress(self):
        result = node_json("g.DFTLabModels.flow.symptoms.map(s => { const m=g.DFTLabModels.flow.createModel(s.key); const blocked=m.next(); const inspected=m.inspect(); const advanced=m.next(); return {key:s.key, blocked:blocked.type, checked:inspected.state.checked, advanced:advanced.type, evidence:inspected.evidence}; })")
        self.assertEqual({item["key"] for item in result}, {"broken-chain", "reset-constraint", "x-source", "capture-timing"})
        for item in result:
            self.assertEqual(item["blocked"], "blocked")
            self.assertEqual(item["checked"], 1)
            self.assertEqual(item["advanced"], "ready")
            self.assertTrue(item["evidence"])

    def test_model_does_not_claim_completion_after_one_check(self):
        result = node_json("(() => { const m=g.DFTLabModels.flow.createModel('capture-timing'); const first=m.inspect(); return {done:first.state.done, remaining:first.state.total-first.state.checked, current:m.getState().current.title}; })()")
        self.assertFalse(result["done"])
        self.assertEqual(result["remaining"], 2)
        self.assertTrue(result["current"])

    def test_reset_clears_evidence_and_keeps_symptom_boundary(self):
        result = node_json("(() => { const m=g.DFTLabModels.flow.createModel('x-source'); m.inspect(); m.next(); m.inspect(); const reset=m.reset(); return {symptom:reset.symptom, checked:reset.checked, cursor:reset.cursor, first:m.inspect().state.cursor}; })()")
        self.assertEqual(result, {"symptom": "x-source", "checked": 0, "cursor": 0, "first": 0})

    def test_broken_chain_is_not_always_observable_with_current_input(self):
        rows=node_json("['normal','open'].flatMap(link=>['0000','1011','1111'].map(stimulus=>g.DFTLabModels.flow.simulate('broken-chain',{link,stimulus})))")
        for row in rows:
            params=row['config']; output=row['trace'][-1][-1]
            self.assertEqual(len(row['trace']),8)
            self.assertEqual(output, params['stimulus'] if params['link']=='normal' else '0000')
            self.assertEqual(row['checks'][1]['issue'], output!=params['stimulus'])
            self.assertEqual(row['checks'][2]['issue'], params['link']=='open')

    def test_documentation_does_not_release_the_reset(self):
        rows=node_json("['yes','no'].flatMap(documented=>[0,1,2,3].map(release=>g.DFTLabModels.flow.simulate('reset-constraint',{documented,release})))")
        for row in rows:
            p=row['config']
            self.assertEqual(row['checks'][0]['issue'],p['documented']=='no')
            self.assertEqual(row['trace'][-1][-1], '10' if p['release']>2 else '11')
            self.assertEqual(row['checks'][1]['issue'],p['release']>2)

    def test_x_mask_and_fault_comparison_are_distinct(self):
        rows=node_json("['X','0','1'].flatMap(source=>['yes','no'].flatMap(mask=>['yes','no'].map(fault=>g.DFTLabModels.flow.simulate('x-source',{source,mask,fault}))))")
        for row in rows:
            p=row['config']; status=row['trace'][-1][-1]
            expected='masked' if p['mask']=='yes' else 'unknown' if p['source']=='X' else 'different' if p['fault']=='yes' else 'same'
            self.assertEqual(status,expected)
            self.assertEqual(row['checks'][2]['issue'],expected!='same')
            if p['source']=='X': self.assertEqual(row['trace'][2][2],'X')

    def test_timing_boundary_and_missing_pulse_are_independent(self):
        rows=node_json("[8,9,12].flatMap(delay=>[1,2].map(pulses=>g.DFTLabModels.flow.simulate('capture-timing',{delay,pulses})))")
        for row in rows:
            p=row['config']
            self.assertEqual(row['checks'][0]['issue'],p['pulses']==1)
            self.assertEqual(row['checks'][1]['issue'],p['delay']>9)
            self.assertEqual(row['checks'][2]['issue'],p['pulses']==1 or p['delay']>9)
            if p['delay']>9 and p['pulses']==2:
                self.assertIn('不作确定推断',row['trace'][-1][-1])

    def test_completion_keeps_issues_and_reconfiguration_invalidates_evidence(self):
        result=node_json("(() => {const m=g.DFTLabModels.flow.createModel('broken-chain');for(let i=0;i<3;i++){m.inspect();m.next();}const done=m.getState();const changed=m.configure({link:'normal',stimulus:'1011'});return {done,changed};})()")
        self.assertTrue(result['done']['done'])
        self.assertEqual(result['done']['issues'],3)
        self.assertEqual(len(result['done']['records']),3)
        self.assertFalse(result['changed']['done'])
        self.assertEqual(result['changed']['checked'],0)
        self.assertEqual(result['changed']['records'],[])

    def test_invalid_configuration_rejected_and_snapshot_is_independent(self):
        result=node_json("(() => {const api=g.DFTLabModels.flow,m=api.createModel('capture-timing');m.inspect();const errors=[];for(const settings of [{delay:-1},{period:0},{setup:'oops'},{pulses:1.5},{delay:Infinity},{delay:null}]){try{m.configure(settings);errors.push(false);}catch(e){errors.push(true);}}const s=m.getState();s.experiment.trace[0][0]='tampered';return {errors,state:m.getState()};})()")
        self.assertEqual(result['errors'],[True]*6)
        self.assertEqual(result['state']['checked'],1)
        self.assertEqual(result['state']['experiment']['trace'][0][0],'Launch')


if __name__ == "__main__":
    unittest.main(verbosity=2)
