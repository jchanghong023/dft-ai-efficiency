"""Exhaustive four-bit Scan checks against an independent integer reference.

Node executes the shipped pure model only; no browser or HDL simulator is used.
"""
from pathlib import Path
import json
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


def node(expression):
    executable = shutil.which('node')
    if not executable:
        raise unittest.SkipTest('Node is required for pure JavaScript model verification')
    result = subprocess.run([executable, '-e',
        "require('./portal/assets/dft.js'); const create=DFTLabModels.scan.create; " + expression],
        cwd=ROOT, capture_output=True, text=True, encoding='utf-8', check=True)
    return json.loads(result.stdout)


def capture(register):
    """Q1 is bit 3, Q4 bit 0. Truth table, independent from the JS array model."""
    q1, q2, q3, q4 = (bool(register & mask) for mask in (8, 4, 2, 1))
    return (8 if q2 != q4 else 0) + (4 if q1 and q3 else 0) + (2 if q2 or q3 else 0) + (1 if not q4 else 0)


class ScanModelTests(unittest.TestCase):
    def test_every_stimulus_and_fault_at_every_edge(self):
        cases = node("const rows=[]; for(let n=0;n<16;n++) for(const fault of ['none','stuck']) {"
                     "const m=create({stimulus:n.toString(2).padStart(4,'0'),fault});"
                     "for(let i=0;i<9;i++)m.step();rows.push(m.getHistory());} console.log(JSON.stringify(rows));")
        detected = 0
        for history in cases:
            stimulus, fault = history[0]['stimulus'], history[0]['fault']
            with self.subTest(stimulus=stimulus, fault=fault):
                self.assertEqual(len(history), 10)
                reg, response = 0, ''
                expected = f'{capture(int(stimulus[::-1], 2)):04b}'[::-1]
                for cycle, event in enumerate(history):
                    self.assertEqual(event['cycle'], cycle)
                    self.assertEqual(event['expected'], expected)
                    self.assertEqual(event['before'], list(map(int, f'{reg:04b}')))
                    if cycle == 5:
                        self.assertEqual(event['d'], list(map(int, f'{capture(reg):04b}')))
                        self.assertEqual(event['se'], 0)
                        self.assertIsNone(event['si'])
                        self.assertIsNone(event['so'])
                        reg = capture(reg)
                        if fault == 'stuck':
                            reg &= ~2
                    elif cycle:
                        serial = int(stimulus[cycle-1]) if cycle <= 4 else 0
                        self.assertEqual(event['se'], 1)
                        self.assertEqual(event['si'], serial)
                        self.assertEqual(event['so'], reg & 1)
                        if cycle > 5:
                            response += str(reg & 1)
                        reg = (serial << 3) | (reg >> 1)
                    self.assertEqual(event['after'], list(map(int, f'{reg:04b}')))
                    self.assertEqual(event['output'], response)
                    self.assertEqual(event['done'], cycle == 9)
                self.assertEqual(history[-1]['result'], 'same' if response == expected else 'different')
                detected += history[-1]['result'] == 'different'
        # Of 16 stimuli, 12 activate this single functional D3 fault; four do not.
        self.assertEqual(detected, 12)

    def test_default_and_unactivated_fault_vectors(self):
        rows = node("console.log(JSON.stringify(['1011','0000'].map(stimulus=>{"
                    "const m=create({stimulus,fault:'stuck'}); for(let i=0;i<9;i++)m.step(); return m.getState();}))); ")
        self.assertEqual((rows[0]['expected'], rows[0]['output'], rows[0]['result']), ('0100', '0000', 'different'))
        self.assertEqual((rows[1]['expected'], rows[1]['output'], rows[1]['result']), ('1000', '1000', 'same'))

    def test_snapshots_cannot_mutate_history_and_reset_is_reproducible(self):
        result = node("const m=create(); const first=m.step(); first.after[0]=9; m.getHistory()[0].before[0]=9;"
                      "const clean=m.getState(); for(let i=0;i<8;i++)m.step(); const last=m.step(),count=m.getHistory().length;"
                      "m.reset(); const reset=m.getHistory(); const again=m.step();"
                      "console.log(JSON.stringify({clean,last,count,reset,again}));")
        self.assertEqual(result['clean'], result['again'])
        self.assertEqual(result['clean']['after'], [1, 0, 0, 0])
        self.assertEqual(result['count'], 10)
        self.assertTrue(result['last']['done'])
        self.assertEqual(len(result['reset']), 1)
        self.assertEqual(result['reset'][0]['before'], [0]*4)

    def test_invalid_settings_rejected_without_destroying_current_run(self):
        result = node("const m=create();m.step(); const errors=[];"
                      "for(const stimulus of ['', '010', '10101', '01x0', 1011, null]) {"
                      "try{m.reset({stimulus});errors.push(false);}catch(e){errors.push(true);}}"
                      "try{m.reset({fault:'invalid'});errors.push(false);}catch(e){errors.push(true);}"
                      "console.log(JSON.stringify({errors,state:m.getState()}));")
        self.assertEqual(result['errors'], [True]*7)
        self.assertEqual(result['state']['cycle'], 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
