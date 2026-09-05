"""Pure model checks for the JTAG, IJTAG and Wrapper teaching labs.

The browser binding is intentionally not exercised here.  Node loads the same
asset through its CommonJS compatibility export and runs deterministic paths.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ASSET = ROOT / "portal" / "assets" / "labs" / "access.js"


def run_node(expression: str) -> dict:
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("Node.js is required for the pure model check")
    script = f"const api=require({json.dumps(str(ASSET))}); {expression}"
    result = subprocess.run([node, "-e", script], cwd=ROOT, text=True, encoding="utf-8",
                            capture_output=True, check=True)
    return json.loads(result.stdout)


class AccessLabFilesTest(unittest.TestCase):
    def test_markers_templates_and_public_api(self) -> None:
        expected = {
            "dft-jtag": "jtag",
            "dft-ijtag": "ijtag",
            "dft-wrapper": "wrapper",
        }
        for stem, marker in expected.items():
            content = (ROOT / "portal" / "content" / f"{stem}.md").read_text(encoding="utf-8")
            self.assertIn(f"<!-- lab:{marker} -->", content)
            template = ROOT / "portal" / "templates" / "labs" / f"{marker}.html"
            self.assertTrue(template.exists())
            source_lines = content.splitlines()
            self.assertGreaterEqual(len(source_lines), 60)
            self.assertLess(len(source_lines), 3000)

    def test_models_are_exported_with_access_prefix(self) -> None:
        result = run_node("console.log(JSON.stringify(Object.keys(api).sort()))")
        self.assertEqual(result, ["accessIjtag", "accessJtag", "accessWrapper"])


class JtagModelTest(unittest.TestCase):
    def test_partial_ir_shift_and_instruction_selected_dr_length(self) -> None:
        result = run_node("""
        const m=api.accessJtag(); m.reset();
        [0,1,1,0,0].forEach(v=>m.step(v,0));
        m.step(1,1); m.step(1,0); m.step(0,0);
        const partial=m.snapshot();
        m.loadInstruction('EXTEST');
        [1,0,0].forEach(v=>m.step(v,0)); const boundary=m.snapshot();
        m.loadInstruction('BYPASS');
        [1,0,0].forEach(v=>m.step(v,0)); const bypass=m.snapshot();
        console.log(JSON.stringify({partial,boundary,bypass}));
        """)
        self.assertEqual(result["partial"]["instruction"], "SAMPLE")
        self.assertEqual(result["boundary"]["state"], "Shift-DR")
        self.assertEqual(len(result["boundary"]["bits"]), 2)
        self.assertEqual(len(result["bypass"]["bits"]), 1)

    def test_string_zero_is_a_zero_bit_and_five_tms_reset_instruction(self) -> None:
        result = run_node("""
        const m=api.accessJtag(); m.reset(); const idle=m.step('0','0');
        [1,1,1,1,1].forEach(v=>m.step(String(v),'0'));
        console.log(JSON.stringify({idle,reset:m.snapshot()}));
        """)
        self.assertEqual(result["idle"]["state"], "Run-Test/Idle")
        self.assertEqual(result["idle"]["tdi"], 0)
        self.assertEqual(result["reset"]["state"], "Test-Logic-Reset")
        self.assertEqual(result["reset"]["instruction"], "BYPASS")

    def test_update_ir_uses_last_two_bits_when_extra_bits_were_shifted(self) -> None:
        result = run_node("""
        const m=api.accessJtag(); m.reset();
        [0,1,1,0,0].forEach(v=>m.step(v,0));
        m.step(0,0); m.step(0,1); m.step(1,1); m.step(1,0); m.step(0,0);
        console.log(JSON.stringify(m.snapshot()));
        """)
        self.assertEqual(result["instruction"], "BYPASS")
        self.assertEqual(result["bits"][-2:], [1, 1])

    def test_tap_reaches_shift_dr_and_updates_tdo(self) -> None:
        expression = """
        const m=api.accessJtag();
        m.reset();
        [0,1,0,0].forEach(v=>m.step(v,1));
        const before=m.snapshot();
        const after=m.step(0,0);
        console.log(JSON.stringify({before, after}));
        """
        result = run_node(expression)
        self.assertEqual(result["before"]["state"], "Shift-DR")
        self.assertEqual(result["after"]["state"], "Shift-DR")
        self.assertTrue(result["before"]["action"].startswith("↑ Capture-DR"))
        self.assertIsNone(result["before"]["tdo"])
        self.assertEqual(result["after"]["tdo"], 0)
        self.assertEqual(result["after"]["tdi"], 0)
        self.assertEqual(result["after"]["cycles"], 5)

    def test_instruction_selection_gates_pin_test(self) -> None:
        result = run_node("""
        const m=api.accessJtag(); m.reset(); const a=m.pinTest();
        m.loadInstruction('EXTEST'); m.setPinStimulus('1'); m.setPinFault('none'); const b=m.pinTest();
        m.setPinFault('open'); const c=m.pinTest();
        m.setPinStimulus('0'); const d=m.pinTest();
        console.log(JSON.stringify({aExpected:a.pinExpected,aActual:a.pinActual,bExpected:b.pinExpected,bActual:b.pinActual,cExpected:c.pinExpected,cActual:c.pinActual,dExpected:d.pinExpected,dActual:d.pinActual,instruction:m.snapshot().instruction}));
        """)
        self.assertEqual((result["aExpected"], result["aActual"]), (None, None))
        self.assertEqual((result["bExpected"], result["bActual"]), (1, 1))
        self.assertEqual((result["cExpected"], result["cActual"]), (1, 0))
        self.assertEqual((result["dExpected"], result["dActual"]), (0, 0))
        self.assertEqual(result["instruction"], "EXTEST")

    def test_update_occurs_on_falling_edge_of_entry_pulse(self):
        result=run_node("""
        const m=api.accessJtag();[0,1,1,0,0].forEach(t=>m.step(t,0));
        m.step(0,0);const exit=m.step(1,0);const update=m.step(1,0);
        const record=m.getHistory().at(-1),idle=m.step(0,0);
        [1,0,0].forEach(t=>m.step(t,0));m.step(0,0);m.step(1,1);
        const dr=m.step(1,0),last=m.getHistory().at(-1);
        console.log(JSON.stringify({exit,update,record,idle,dr,last}));
        """)
        self.assertEqual(result['exit']['instruction'],'BYPASS')
        self.assertEqual((result['update']['state'],result['update']['instruction']),('Update-IR','EXTEST'))
        self.assertEqual(result['record']['before']['instruction'],'BYPASS')
        self.assertIn('Update-IR',result['record']['falling'])
        self.assertEqual(result['idle']['instruction'],'EXTEST')
        self.assertEqual((result['dr']['state'],result['dr']['pinStimulus']),('Update-DR',1))
        self.assertIn('提交边界驱动 1',result['last']['falling'])

    def test_pause_holds_bits_and_exit_shift_still_shifts_last_bit(self):
        result=run_node("""
        const m=api.accessJtag();[0,1,1,0,0].forEach(t=>m.step(t,0));
        const exit=m.step(1,1);m.step(0,0);const paused=m.step(0,1),still=m.step(0,0);
        m.step(1,0);const resumed=m.step(0,1),shifted=m.step(0,0);
        console.log(JSON.stringify({exit,paused,still,resumed,shifted}));
        """)
        self.assertEqual(result['exit']['bits'],[0,1])
        self.assertEqual(result['exit']['tdo'],1)
        for key in ('paused','still','resumed'):
            self.assertEqual(result[key]['bits'],[0,1])
            self.assertIsNone(result[key]['tdo'])
        self.assertEqual(result['shifted']['bits'],[1,0])

    def test_all_sixteen_states_and_thirty_two_tms_transitions(self):
        # Protocol transition oracle, independent of the page's exported table.
        result=run_node("""
        const table={
          'Test-Logic-Reset':['Run-Test/Idle','Test-Logic-Reset'],
          'Run-Test/Idle':['Run-Test/Idle','Select-DR-Scan'],
          'Select-DR-Scan':['Capture-DR','Select-IR-Scan'],
          'Select-IR-Scan':['Capture-IR','Test-Logic-Reset']};
        for(const r of ['DR','IR']){
          table['Capture-'+r]=['Shift-'+r,'Exit1-'+r];table['Shift-'+r]=['Shift-'+r,'Exit1-'+r];
          table['Exit1-'+r]=['Pause-'+r,'Update-'+r];table['Pause-'+r]=['Pause-'+r,'Exit2-'+r];
          table['Exit2-'+r]=['Shift-'+r,'Update-'+r];table['Update-'+r]=['Run-Test/Idle','Select-DR-Scan'];
        }
        const routes={'Test-Logic-Reset':[]},queue=['Test-Logic-Reset'];
        while(queue.length){const key=queue.shift();table[key].forEach((dest,tms)=>{if(!(dest in routes)){routes[dest]=[...routes[key],tms];queue.push(dest);}});}
        const rows=[];
        for(const [state,route] of Object.entries(routes))for(const tms of [0,1]){
          const m=api.accessJtag();route.forEach(t=>m.step(t,0));const before=m.snapshot().state;
          const next=m.step(tms,0).state;for(let i=0;i<5;i++)m.step(1,0);
          rows.push({state,before,next,expected:table[state][tms],reset:m.snapshot().state});
        }
        console.log(JSON.stringify(rows));
        """)
        self.assertEqual(len(result),32)
        for row in result:
            self.assertEqual(row['before'],row['state'])
            self.assertEqual(row['next'],row['expected'])
            self.assertEqual(row['reset'],'Test-Logic-Reset')

    def test_changed_conditions_invalidate_results_and_history_is_immutable(self):
        result=run_node("""
        const m=api.accessJtag();m.setPinStimulus(1);m.setPinFault('open');
        const loaded=m.loadInstruction('EXTEST'),tested=m.pinTest();
        const changed=m.setPinFault('none');m.pinTest();const changedStim=m.setPinStimulus(0);
        const history=m.getHistory();history[0].after.bits.push(9);history[7].after.instruction='tampered';
        const intact=m.getHistory();m.reset();
        console.log(JSON.stringify({loaded,tested,changed,changedStim,intact,count:m.getHistory().length}));
        """)
        self.assertEqual((result['loaded']['pinStimulus'],result['loaded']['pinFault']),(1,'open'))
        self.assertIn('检出差异',result['tested']['pinResult'])
        self.assertIsNone(result['changed']['pinActual'])
        self.assertIsNone(result['changedStim']['pinExpected'])
        self.assertNotIn(9,result['intact'][0]['after']['bits'])
        self.assertEqual(result['intact'][7]['after']['instruction'],'EXTEST')
        self.assertEqual(result['count'],0)


class IjtagModelTest(unittest.TestCase):
    def test_sib_changes_path_length_and_instrument_visibility(self) -> None:
        result = run_node("""
        const m=api.accessIjtag(); const closed=m.snapshot();
        m.setBit('1'); m.shift(); const staged=m.snapshot();
        m.updateSib(); const open=m.snapshot();
        m.setBit('1'); m.shift(); const shifted=m.snapshot();
        m.updateInstrument(); const committed=m.snapshot();
        m.setBit('0'); m.shift(); m.updateSib(); const closedAgain=m.snapshot();
        m.setBit('1'); m.shift(); const closedShift=m.snapshot(); m.updateSib(); const reopened=m.snapshot();
        console.log(JSON.stringify({closed,staged,open,shifted,committed,closedAgain,closedShift,reopened}));
        """)
        self.assertEqual(result["closed"]["length"], 1)
        self.assertEqual(result["closed"]["instrumentValue"], "不可见")
        self.assertEqual(result["staged"]["stagedSib"], 1)
        self.assertEqual(result["staged"]["instrumentValue"], "不可见")
        self.assertEqual(result["open"]["length"], 9)
        self.assertEqual(result["shifted"]["instrumentValue"], "00000000")
        self.assertEqual(result["committed"]["instrumentValue"], "10000000")
        self.assertEqual(result["closedAgain"]["length"], 1)
        self.assertEqual(result["closedShift"]["stagedSib"], 1)
        self.assertEqual(result["reopened"]["instrumentValue"], "10000000")


class WrapperModelTest(unittest.TestCase):
    def test_three_modes_have_distinct_isolation_semantics(self) -> None:
        result = run_node("""
        const m=api.accessWrapper(); m.setInput('1');
        const internal=m.setMode('internal'); m.apply(); const i=m.snapshot();
        m.setMode('external'); m.setLinkMode('normal'); m.apply(); const e=m.snapshot();
        m.setLinkMode('invert'); m.apply(); const ei=m.snapshot();
        m.setMode('bypass'); m.apply(); const b=m.snapshot();
        m.setMode('internal'); const cleared=m.snapshot();
        console.log(JSON.stringify({i,e,ei,b,cleared}));
        """)
        self.assertTrue(result["i"]["isolated"])
        self.assertFalse(result["e"]["isolated"])
        self.assertTrue(result["b"]["isolated"])
        self.assertEqual([result[k]["output"] for k in ("i", "e", "b")], [0, 1, 1])
        self.assertEqual(result["i"]["coreInput"], 1)
        self.assertEqual(result["i"]["coreOutput"], 0)
        self.assertIsNone(result["e"]["coreInput"])
        self.assertIsNone(result["e"]["coreOutput"])
        self.assertEqual(result["e"]["neighbor"], 1)
        self.assertEqual(result["ei"]["neighbor"], 0)
        self.assertEqual(result["b"]["bypassReg"], 1)
        self.assertFalse(result["cleared"]["applied"])
        self.assertIsNone(result["cleared"]["output"])


if __name__ == "__main__":
    unittest.main()
