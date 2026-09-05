"""Generated layout contracts and optional pure DOM checks (not browser/visual acceptance).

DOM dependency: npm install --prefix .tmp/dom-check --cache .tmp/npm-cache
linkedom@0.18.12 --ignore-scripts --no-audit --no-fund
"""
from pathlib import Path
import json
import re
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

NODE_TEST = r'''
const assert = require('node:assert/strict'), fs = require('node:fs'), path = require('node:path'), vm = require('node:vm');
const {parseHTML} = require(path.join(process.cwd(), '.tmp/dom-check/node_modules/linkedom'));
function load(relative, options={}) {
  const local=new URL(relative,'file:///'), full=path.join(process.cwd(),'site',local.pathname), {window}=parseHTML(fs.readFileSync(full,'utf8'));
  const document=window.document, intervals=new Map(); let timer=0;
  // Minimal DOM emulation gaps: layout, dialog and form selection. No browser is launched.
  Object.defineProperty(window.HTMLSelectElement.prototype,'value',{configurable:true,get(){const o=this.querySelector('option[selected]')||this.querySelector('option');return o?o.value:'';},set(v){this.querySelectorAll('option').forEach(o=>o.toggleAttribute('selected',o.value===String(v)));}});
  Object.defineProperty(window.HTMLInputElement.prototype,'checked',{configurable:true,get(){return this.hasAttribute('checked');},set(v){this.toggleAttribute('checked',!!v);}});
  window.HTMLElement.prototype.scrollIntoView=function(){};
  document.querySelectorAll('dialog').forEach(d=>{d.showModal=()=>d.open=true;d.close=()=>d.open=false;});
  const storage=options.storage||new Map(), timeouts=new Map();
  let now=options.now||new Date(2026,8,5,12,0,0);
  class Clock extends Date { constructor(...args){super(...(args.length?args:[now.getTime()]));} }
  const sandbox={document,console,URL,Date:Clock,MutationObserver:window.MutationObserver,Event:window.Event,
    localStorage:{getItem:k=>{if(options.blockStorage)throw Error('Storage unavailable');return storage.get(k)||null;},setItem:(k,v)=>{if(options.blockStorage)throw Error('Storage unavailable');storage.set(k,v);},removeItem:k=>{if(options.blockStorage)throw Error('Storage unavailable');storage.delete(k);}},
    navigator:{},location:{href:'file:///'+full.replaceAll('\\','/')+local.search+local.hash},
    matchMedia:()=>({matches:false,addEventListener(){}}),
    requestAnimationFrame:f=>{f();return 1;},setTimeout:(f,ms)=>{timeouts.set(++timer,{f,ms});return timer;},clearTimeout:id=>timeouts.delete(id),
    setInterval:(f,ms)=>{intervals.set(++timer,{f,ms});return timer;},clearInterval:id=>intervals.delete(id),
    addEventListener:window.addEventListener.bind(window),removeEventListener:window.removeEventListener.bind(window)};
  sandbox.window=sandbox; const context=vm.createContext(sandbox);
  for(const script of document.querySelectorAll('script[src]')){
    const source=path.resolve(path.dirname(full),script.getAttribute('src'));
    vm.runInContext(fs.readFileSync(source,'utf8'),context,{filename:source});
  }
  document.dispatchEvent(new window.Event('DOMContentLoaded'));
  const click=node=>{assert(node,'control exists'); node.dispatchEvent(new window.Event('click'));};
  const change=node=>node.dispatchEvent(new window.Event('change'));
  return {document,window,click,change,intervals,context,timeouts,storage,setTime:value=>{now=value;}};
}
const home=load('index.html');
assert(home.document.querySelector('#home-title').textContent.includes('AI 开发有依据'));
const homeSearch=home.document.querySelector('#search-input');
homeSearch.value='模型';homeSearch.dispatchEvent(new home.window.Event('input'));
assert(home.document.querySelector('.search-result').getAttribute('href').startsWith('pages/command-model.html?'),'Model selection outranks incidental mentions');
homeSearch.value='/resume';homeSearch.dispatchEvent(new home.window.Event('input'));
assert(home.document.querySelector('.search-result').getAttribute('href').startsWith('pages/command-resume.html?'),'Exact command is first');
assert(!home.document.querySelector('[data-copy="/model"]').hidden,'Command copy is available with JavaScript');
for(const href of ['pages/quickstart.html','pages/team.html','pages/command-resume.html','pages/command-model.html','pages/command-compact.html']){
  assert(home.document.querySelector('main a[href="'+href+'"]'),'High-value entry: '+href);
}
const theme=p=>p.document.documentElement.dataset.theme;
assert.equal(theme(home),'light');
assert(!home.document.querySelector('.theme-controls').hidden);
home.click(home.document.querySelector('#theme-toggle'));
assert.equal(theme(home),'dark');
assert.equal(home.storage.get('dft-theme'),'dark');
assert.equal(home.document.querySelector('#theme-toggle').getAttribute('aria-label'),'切换到浅色模式');
assert.equal(home.document.querySelector('#theme-auto').getAttribute('aria-pressed'),'false');
const saved=load('pages/quickstart.html',{storage:home.storage});
assert.equal(theme(saved),'dark','Manual choice persists on navigation');
saved.click(saved.document.querySelector('#theme-toggle'));
assert.equal(theme(saved),'light');
home.click(home.document.querySelector('#theme-auto'));
assert.equal(theme(home),'light');
assert.equal(home.storage.has('dft-theme'),false);
assert.equal(home.document.querySelector('#theme-auto').getAttribute('aria-pressed'),'true');
for(const [hour,minute,expected] of [[0,0,'dark'],[6,59,'dark'],[7,0,'light'],[18,59,'light'],[19,0,'dark'],[23,59,'dark']]){
  assert.equal(theme(load('index.html',{now:new Date(2026,8,5,hour,minute)})),expected,'Automatic boundary '+hour+':'+minute);
}
const sunset=load('index.html',{now:new Date(2026,8,5,18,59,59)});
assert.equal(sunset.timeouts.size,1);
const boundary=[...sunset.timeouts.values()][0];
assert.equal(boundary.ms,1050);
sunset.setTime(new Date(2026,8,5,19,0,0));boundary.f();
assert.equal(theme(sunset),'dark','An open page switches at sunset');
sunset.click(sunset.document.querySelector('#theme-toggle'));
assert.equal(sunset.timeouts.size,0,'Manual preference stops automatic scheduling');
sunset.setTime(new Date(2026,8,5,23,0));
sunset.window.dispatchEvent(new sunset.window.Event('pageshow'));
assert.equal(theme(sunset),'light','Manual override survives returning at night');
sunset.click(sunset.document.querySelector('#theme-auto'));
assert.equal(theme(sunset),'dark','Auto reset uses current time');
const sunrise=load('index.html',{now:new Date(2026,8,5,6,59,59)});
const dawn=[...sunrise.timeouts.values()][0];sunrise.setTime(new Date(2026,8,5,7,0));dawn.f();
assert.equal(theme(sunrise),'light','An open page switches at sunrise');
const blocked=load('index.html',{blockStorage:true});
blocked.click(blocked.document.querySelector('#theme-toggle'));
assert.equal(theme(blocked),'dark','Storage denial must not disable switching');
blocked.click(blocked.document.querySelector('#theme-auto'));
assert.equal(theme(blocked),'light');
const invalid=load('index.html',{storage:new Map([['dft-theme','invalid']]),now:new Date(2026,8,5,22)});
assert.equal(theme(invalid),'dark','Unknown stored values fall back to automatic');
const sibling=new invalid.window.Event('storage');sibling.key='dft-theme';invalid.storage.set('dft-theme','light');invalid.window.dispatchEvent(sibling);
assert.equal(theme(invalid),'light','Other-page preferences refresh');

const index=JSON.parse(fs.readFileSync('site/assets/search-data.js','utf8').replace(/^window.DFT_SEARCH = /,'').replace(/;\s*$/,''));
for(const entry of ['pages/quickstart.html','pages/team.html','pages/maintenance.html','pages/dft-scan.html']){
  const p=load(entry), d=p.document;
  const input=d.querySelector('#search-input'); input.value='DFT'; input.dispatchEvent(new p.window.Event('input'));
  for(const link of d.querySelectorAll('.search-result')){
    const target=path.posix.normalize(path.posix.join(path.posix.dirname(entry),link.getAttribute('href').split(/[?#]/)[0]));
    assert.equal(index.find(item=>item.url===target).area,d.body.dataset.area);
  }
}
const doc=load('pages/quickstart.html');
assert(doc.document.querySelector('aside.toc a.current'));
const code=doc.document.querySelector('pre code');
if(code){const {document:raw}=parseHTML(fs.readFileSync('site/pages/quickstart.html','utf8'));assert.equal(code.textContent,raw.querySelector('pre code').textContent);assert(doc.document.querySelector('.code-language'));}
const nav=doc.document.querySelector('#nav-filter');nav.value='不存在的标题';nav.dispatchEvent(new doc.window.Event('input'));
assert([...doc.document.querySelectorAll('.module-navigation a')].every(a=>a.hidden));
const search=load('start/index.html'), box=search.document.querySelector('#search-input');
box.value='OMP';box.dispatchEvent(new search.window.Event('input'));
assert.equal(search.document.querySelectorAll('.search-result').length,40);
assert(!search.document.querySelector('.search-more').hidden);
while(!search.document.querySelector('.search-more').hidden)search.click(search.document.querySelector('.search-more'));
assert.equal(search.document.querySelectorAll('.search-result').length,index.filter(i=>i.area==='start'&&(i.title+' '+i.text).toLowerCase().includes('omp')).length);
box.value='fullsend';box.dispatchEvent(new search.window.Event('input'));
assert(search.document.querySelectorAll('.search-result').length<40);
assert(search.document.querySelector('.search-more').hidden);
const found=search.document.querySelector('.search-result'); assert(found.getAttribute('href').includes('?q=fullsend'));
assert(search.document.querySelector('mark.search-hit'));
const highlightDoc=load('pages/quickstart.html?q=python3.11');
assert(highlightDoc.document.querySelector('.article mark.search-hit'));
const original=parseHTML(fs.readFileSync('site/pages/quickstart.html','utf8')).document;
assert.equal(highlightDoc.document.querySelector('pre code').textContent,original.querySelector('pre code').textContent);
highlightDoc.click(highlightDoc.document.querySelector('.search-context button'));
assert(highlightDoc.document.querySelector('mark.active-hit'));
highlightDoc.click(highlightDoc.document.querySelector('.search-context button:last-child'));
assert(!highlightDoc.document.querySelector('mark.search-hit'));
assert.equal(JSON.stringify(search.context.DFTSearch.ranges('😀 ＰＡＤ ﬀ',['pad','ff'])),JSON.stringify([[3,6],[7,8]]));

const lessons=JSON.parse(fs.readFileSync('portal/metadata/dft-curriculum.json','utf8')).groups.flatMap(g=>g.lessons);
for(const lesson of lessons.filter(l=>l.lab||['dft-scan','dft-edt'].includes(l.slug))){
  const p=load('pages/'+lesson.slug+'.html'),d=p.document, lab=d.querySelector('.dft-lab,.dft-demo');
  assert([...lab.querySelectorAll('button')].some(b=>!b.disabled),lesson.slug+' controls bind');
  const toolbar=lab.querySelector('.drawing-toolbar');
  if(toolbar){
    p.click(toolbar.querySelector('[aria-label="放大电路"]'));
    assert.equal(lab.querySelector('svg').style.width,'125%');
    p.click(toolbar.querySelector('[aria-label="适应画布"]'));
    assert.equal(lab.querySelector('svg').style.width,'100%');
    const text=lab.querySelector('svg text');p.click(text);assert(lab.querySelector('.signal-detail').textContent.includes(text.textContent.trim()));
  }
  const step=lab.querySelector('[data-action="step"]');
  if(step&&!step.disabled)p.click(step);
  const reset=lab.querySelector('[data-action="reset"]');if(reset&&!reset.disabled)p.click(reset);
}
for(const slug of ['dft-scan','dft-edt','dft-memory-bist','dft-logic-bist']){
  const p=load('pages/'+slug+'.html'),lab=p.document.querySelector('.dft-lab,.dft-demo');
  const step=lab.querySelector('[data-action="step"]'),play=lab.querySelector('[data-action="play"]'),speed=lab.querySelector('[data-setting="speed"]');
  p.click(play);assert.equal(p.intervals.size,1);const before=[...p.intervals.values()][0].ms;
  speed.value='2';p.change(speed);assert.equal(p.intervals.size,1);assert.equal([...p.intervals.values()][0].ms,before/2);
  p.click(play);assert.equal(p.intervals.size,0);
  for(let i=0;i<9&&!step.disabled;i++)p.click(step);
  if(slug==='dft-scan')assert.equal(lab.querySelector('[data-field="output"]').textContent,'0100');
  if(slug==='dft-logic-bist')assert.equal(lab.querySelector('[data-field="signature"]').textContent,'1000');
}
const scanPage=load('pages/dft-scan.html'),scan=scanPage.document.querySelector('#scan-demo');
const scanStep=scan.querySelector('[data-action="step"]'), scanPlay=scan.querySelector('[data-action="play"]');
for(let i=0;i<6;i++)scanPage.click(scanStep);
scanPage.click(scanPlay);assert.equal(scanPage.intervals.size,1);
scanPage.click(scan.querySelector('[data-edge="5"]'));assert.equal(scanPage.intervals.size,0);
assert.equal(scan.dataset.step,'6');assert.equal(scan.dataset.viewStep,'5');
assert.equal(scan.querySelector('[data-field="registers"]').textContent,'0010');
assert.equal(scan.querySelector('[data-field="se"]').textContent,'0');
assert.equal(scan.querySelector('[data-field="output"]').textContent,'尚未移出');
scanPage.click(scan.querySelector('[data-inspect="q2"]'));
assert(scan.querySelector('[data-field="component-detail"]').textContent.includes('D3=1'));
scanPage.click(scanStep);assert.equal(scan.dataset.step,'7');assert.equal(scan.dataset.viewStep,'7');
scanPage.click(scan.querySelector('[data-edge="0"]'));
scanPage.click(scan.querySelector('[data-action="latest"]'));assert.equal(scan.dataset.viewStep,'7');
const scanFault=scan.querySelector('[data-setting="fault"]');scanFault.value='stuck';scanPage.change(scanFault);
for(const bit of scan.querySelectorAll('[data-stimulus]')){bit.value='0';scanPage.change(bit);}
assert.equal(scan.dataset.step,'0');assert.equal(scan.querySelectorAll('[data-edge]').length,1);
assert.equal(scan.querySelector('[data-field="expected"]').textContent,'1000');
for(let i=0;i<9;i++)scanPage.click(scanStep);
assert.equal(scan.querySelector('[data-field="output"]').textContent,'1000');assert.equal(scan.dataset.result,'same');
assert(scan.querySelector('[data-field="explanation"]').textContent.includes('没有激活'));
scanPage.click(scan.querySelector('[data-edge="5"]'));assert(scanStep.disabled);assert(scanPlay.disabled);
assert.equal(scan.querySelector('[data-edge="5"]').getAttribute('aria-pressed'),'true');
assert.equal(scan.querySelector('[data-field="registers"]').textContent,'0001');
assert(scan.querySelector('[data-field="component-detail"]').textContent.includes('无故障值 0'));
const flowPage=load('pages/dft-flow.html'),flow=flowPage.document.querySelector('#flow-lab');
const inspect=flow.querySelector('[data-action="inspect"]'),next=flow.querySelector('[data-action="next"]');
assert(next.disabled);flowPage.click(inspect);assert(!next.disabled);
assert.equal(flow.querySelectorAll('[data-evidence-records] li').length,1);
flowPage.click(next);flowPage.click(inspect);flowPage.click(next);flowPage.click(inspect);flowPage.click(next);
assert.equal(flow.dataset.state,'attention');assert(inspect.disabled);
assert(flow.querySelector('[data-field="confidence"]').textContent.includes('异常'));
const link=flow.querySelector('[data-parameter="link"]');link.value='normal';flowPage.change(link);
assert.equal(flow.dataset.progress,'0');assert.equal(flow.querySelectorAll('[data-evidence-records] li').length,0);
assert.equal(flow.querySelector('[data-trace-body] tr:last-child td:last-child').textContent,'1011');
const symptom=flow.querySelector('[data-setting="symptom"]');symptom.value='x-source';flowPage.change(symptom);
assert(flow.querySelector('[data-flow-options="broken-chain"]').hidden);
assert(!flow.querySelector('[data-flow-options="x-source"]').hidden);
const source=flow.querySelector('[data-parameter="source"]'),mask=flow.querySelector('[data-parameter="mask"]'),faultControl=flow.querySelector('[data-parameter="fault"]');
source.value='0';mask.value='yes';faultControl.value='yes';flowPage.change(mask);
assert.equal(flow.querySelector('[data-trace-body] tr:last-child td:last-child').textContent,'masked');
mask.value='no';flowPage.change(mask);
assert.equal(flow.querySelector('[data-trace-body] tr:last-child td:last-child').textContent,'different');
const jtagPage=load('pages/dft-jtag.html'),jtag=jtagPage.document.querySelector('#jtag-lab');
const jtagInstruction=jtag.querySelector('[data-access-setting="instruction"]'),pinFault=jtag.querySelector('[data-access-setting="pin-fault"]'),pinStimulus=jtag.querySelector('[data-access-setting="pin-stimulus"]');
pinFault.value='open';jtagPage.change(pinFault);pinStimulus.value='1';jtagPage.change(pinStimulus);
jtagInstruction.value='EXTEST';jtagPage.change(jtagInstruction);jtagPage.click(jtag.querySelector('[data-access-action="load-instruction"]'));
assert.equal(jtag.querySelectorAll('[data-tck]').length,9);assert.equal(pinFault.value,'open');
jtagPage.click(jtag.querySelector('[data-tck="8"]'));
assert.equal(jtag.dataset.liveCycle,'9');assert.equal(jtag.dataset.viewCycle,'8');
assert.equal(jtag.querySelector('[data-access-field="state"]').textContent,'Update-IR');
assert.equal(jtag.querySelector('[data-access-field="instruction"]').textContent,'EXTEST');
jtagPage.click(jtag.querySelector('[data-tap-state="Pause-IR"]'));
assert(jtag.querySelector('[data-access-field="node-detail"]').textContent.includes('保存当前移位寄存器'));
assert.equal(jtag.dataset.liveCycle,'9');
jtagPage.click(jtag.querySelector('[data-access-action="tms0"]'));
assert.equal(jtag.dataset.liveCycle,'10');assert.equal(jtag.dataset.viewCycle,'10');
jtagPage.click(jtag.querySelector('[data-access-action="pin-test"]'));
assert(jtag.querySelector('[data-access-field="pin-result"]').textContent.includes('检出差异'));
pinFault.value='none';jtagPage.change(pinFault);
assert(jtag.querySelector('[data-access-field="pin-result"]').textContent.includes('尚未执行'));
const occPage=load('pages/dft-clock-reset.html'),occ=occPage.document.querySelector('#clocks-occ-lab');
const occMode=occ.querySelector('[data-field="mode"]'),se=occ.querySelector('[data-field="se"]'),functional=occ.querySelector('[data-field="functional"]');
occMode.value='capture';se.checked=false;functional.checked=true;occPage.change(occMode);
const occStep=occ.querySelector('[data-action="step"]'),occPlay=occ.querySelector('[data-action="play"]');
occPage.click(occPlay);assert.equal(occPage.intervals.size,1);
occ.querySelector('[data-setting="speed"]').value='2';occPage.change(occ.querySelector('[data-setting="speed"]'));
assert.equal([...occPage.intervals.values()][0].ms,425);
[...occPage.intervals.values()][0].f();[...occPage.intervals.values()][0].f();
assert.equal(occ.querySelector('[data-readout="edges"]').textContent,'2 / 2');
occPage.click(occ.querySelector('[data-occ-edge="1"]'));assert.equal(occPage.intervals.size,0);
assert.equal(occ.dataset.step,'2');assert.equal(occ.dataset.viewStep,'1');
assert.equal(occ.querySelector('[data-readout="edges"]').textContent,'1 / 2');
occPage.click(occStep);assert.equal(occ.dataset.step,'3');
assert.equal(occ.querySelector('[data-readout="pulses"]').textContent,'本沿未放行');
assert.equal(occ.querySelectorAll('[data-visual="pulse"][data-active="true"]').length,2);
occPage.click(occStep);assert(occStep.disabled);assert(occPlay.disabled);
functional.checked=false;occPage.change(functional);assert(occStep.disabled);
assert.equal(occ.querySelector('[data-readout="edges"]').textContent,'0 / 0');
assert.equal(occ.querySelectorAll('[data-occ-edge]').length,1);
console.log('PASS home, document and lab DOM contracts including Scan/OCC/TAP history and computed flow evidence');
'''


class PresentationTests(unittest.TestCase):
    def test_section_index_retains_unicode_ids_and_separates_evidence(self):
        from scripts._lib.search import section_index
        rows=section_index('<h2 id="输入">输入 <code>SI</code></h2><p>刺激 1011</p><h2 id="输出">输出</h2><p>响应 0100</p>')
        self.assertEqual([row['id'] for row in rows],['输入','输出'])
        self.assertIn('SI',rows[0]['title'])
        self.assertIn('1011',rows[0]['text'])
        self.assertNotIn('0100',rows[0]['text'])
        self.assertIn('0100',rows[1]['text'])

    def test_home_and_article_assets_are_separate(self):
        home = (ROOT/'site/index.html').read_text(encoding='utf-8')
        body = home.split('<main', 1)[1].split('</main>', 1)[0]
        self.assertNotIn('dft/index.html', body)
        self.assertNotIn('internal/index.html', body)
        self.assertNotIn('class="sidebar', home)
        self.assertIn('assets/home.css', home)
        self.assertNotIn('assets/home.js', home)
        self.assertIn('assets/theme.js', home)
        self.assertLess(home.index('assets/theme.js'), home.index('assets/style.css'))
        self.assertNotIn('assets/reading.js', home)
        page = (ROOT/'site/pages/quickstart.html').read_text(encoding='utf-8')
        self.assertIn('aria-label="本页导航"', page)
        self.assertNotIn('assets/home.js', page)
        self.assertNotIn('assets/dft.js', page)

    def test_labs_precede_reading_and_search_has_explicit_areas(self):
        curriculum=json.loads((ROOT/'portal/metadata/dft-curriculum.json').read_text(encoding='utf-8'))
        for lesson in [l for group in curriculum['groups'] for l in group['lessons'] if l.get('lab')]:
            page=(ROOT/f"site/pages/{lesson['slug']}.html").read_text(encoding='utf-8').split('<main',1)[1]
            self.assertLess(re.search(r'<section\b[^>]*\bdft-lab\b', page).start(), page.index('<p>'))
        raw=(ROOT/'site/assets/search-data.js').read_text(encoding='utf-8')
        rows=json.loads(raw.removeprefix('window.DFT_SEARCH = ').rstrip(';\n'))
        self.assertEqual({r['area'] for r in rows},{'start','team','maintenance','internal','dft'})

    def test_pure_dom_interactions(self):
        node=shutil.which('node')
        if not node or not (ROOT/'.tmp/dom-check/node_modules/linkedom').is_dir():
            self.skipTest('Optional linkedom DOM emulator not installed; see module docstring')
        result=subprocess.run([node,'-e',NODE_TEST],cwd=ROOT,capture_output=True,text=True,encoding='utf-8')
        self.assertEqual(result.returncode,0,result.stdout+'\n'+result.stderr)

if __name__=='__main__': unittest.main(verbosity=2)
