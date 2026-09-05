"use strict";
(() => {
  // One step is a full TCK pulse: rising-edge capture/shift and transition,
  // then falling-edge Update in the entered state. TDO is the bit sampled out.
  const transitions = {
    "Test-Logic-Reset": {0:"Run-Test/Idle",1:"Test-Logic-Reset"}, "Run-Test/Idle": {0:"Run-Test/Idle",1:"Select-DR-Scan"},
    "Select-DR-Scan": {0:"Capture-DR",1:"Select-IR-Scan"}, "Capture-DR": {0:"Shift-DR",1:"Exit1-DR"}, "Shift-DR": {0:"Shift-DR",1:"Exit1-DR"},
    "Exit1-DR": {0:"Pause-DR",1:"Update-DR"}, "Pause-DR": {0:"Pause-DR",1:"Exit2-DR"}, "Exit2-DR": {0:"Shift-DR",1:"Update-DR"}, "Update-DR": {0:"Run-Test/Idle",1:"Select-DR-Scan"},
    "Select-IR-Scan": {0:"Capture-IR",1:"Test-Logic-Reset"}, "Capture-IR": {0:"Shift-IR",1:"Exit1-IR"}, "Shift-IR": {0:"Shift-IR",1:"Exit1-IR"},
    "Exit1-IR": {0:"Pause-IR",1:"Update-IR"}, "Pause-IR": {0:"Pause-IR",1:"Exit2-IR"}, "Exit2-IR": {0:"Shift-IR",1:"Update-IR"}, "Update-IR": {0:"Run-Test/Idle",1:"Select-DR-Scan"}
  };
  // Teaching opcodes only (LSB-first shift order): EXTEST=00, SAMPLE=01, BYPASS=11.
  const instructionBits = {EXTEST:"00", SAMPLE:"01", BYPASS:"11"};
  const bitInstruction = {"00":"EXTEST", "01":"SAMPLE", "11":"BYPASS"};
  const bitValue = value => (value === 1 || value === "1") ? 1 : 0;

  function jtag() {
    let history=[];
    const copy=value=>JSON.parse(JSON.stringify(value));
    const m = {state:"Test-Logic-Reset", cycles:0, tdi:1, bits:[], irShift:[], instruction:"BYPASS", pending:"BYPASS", tdo:null, action:"复位", pinStimulus:0, pinFault:"none", pinResult:"尚未执行", pinExpected:null, pinActual:null};
    const pathOf = state => state.includes("IR") ? "IR" : state.includes("DR") ? "DR" : "—";
    const snapshot = () => ({state:m.state, cycles:m.cycles, tdi:m.tdi, path:pathOf(m.state), bits:m.bits.slice(), instruction:m.instruction, pending:m.pending, tdo:m.tdo, action:m.action, pinStimulus:m.pinStimulus, pinFault:m.pinFault, pinExpected:m.pinExpected, pinActual:m.pinActual, pinResult:m.pinResult, nextStates:{...transitions[m.state]}});
    const clearPin=()=>{m.pinExpected=null;m.pinActual=null;m.pinResult='尚未执行：条件改变后需重新比较';};
    const reset = () => { Object.assign(m, {state:"Test-Logic-Reset",cycles:0,tdi:1,bits:[],irShift:[],instruction:"BYPASS",pending:"BYPASS",tdo:null,action:"复位到 Test-Logic-Reset",pinStimulus:0,pinFault:"none",pinResult:"尚未执行",pinExpected:null,pinActual:null}); history=[]; return snapshot(); };
    const step = (tms, tdi = m.tdi) => {
      const previous=snapshot(),before=m.state, inBit=bitValue(tdi), tmsBit=bitValue(tms); m.tdi=inBit; m.tdo=null;
      if(before==="Capture-DR"){const sensed=m.pinFault==="open"?0:m.pinFault==="short"?1:m.pinStimulus;m.bits=m.instruction==="BYPASS"?[0]:[sensed,m.pinStimulus];m.action=m.instruction==="BYPASS"?"Capture-DR：旁路寄存器捕获 0":"Capture-DR：示例边界寄存器捕获 [接收值, 驱动值]";}
      else if(before==="Capture-IR"){m.bits=[1,0];m.irShift=[];m.action="Capture-IR：装入指令捕获模式";}
      else if(before==="Shift-DR"||before==="Shift-IR"){m.tdo=m.bits.length?m.bits.shift():0;m.bits.push(inBit);if(before==="Shift-IR")m.irShift.push(inBit);m.action=`${before}：TDI=${inBit}，TDO=${m.tdo}`;}
      else m.action=`${before}：只按 TMS 选择下一状态`;
      const rising=m.action;let falling='无 Update 提交';
      m.state=transitions[before][tmsBit];m.cycles++;
      if(m.state==='Update-IR') {
        const decoded=bitInstruction[m.bits.join('')];
        if(decoded){m.instruction=decoded;m.pending=decoded;}
        falling=`Update-IR：${decoded||'未定义编码，教学模型保留当前指令'}`;clearPin();
      } else if(m.state==='Update-DR'&&m.instruction==='EXTEST') {
        m.pinStimulus=m.bits[1]||0;falling=`Update-DR：提交边界驱动 ${m.pinStimulus}`;clearPin();
      }
      if(m.state==="Test-Logic-Reset"){m.instruction="BYPASS";m.pending="BYPASS";m.irShift=[];m.bits=[];clearPin();}
      m.action=`↑ ${rising}；↓ ${falling}`;
      history.push({cycle:m.cycles,tms:tmsBit,tdi:inBit,tdo:m.tdo,before:previous,after:snapshot(),rising,falling});
      return snapshot();
    };
    const loadInstruction = value => { const requested=Object.prototype.hasOwnProperty.call(instructionBits,value)?value:"BYPASS";const stim=m.pinStimulus,fault=m.pinFault;reset();m.pinStimulus=stim;m.pinFault=fault;const bits=instructionBits[requested];const sequence=[[0,0],[1,0],[1,0],[0,0],[0,0],[0,Number(bits[0])],[1,Number(bits[1])],[1,0],[0,0]];sequence.forEach(pair=>step(pair[0],pair[1]));m.pending=requested;m.action=`已从 TAP 复位生成九拍 IR 序列；第 8 拍下降沿提交，逐拍输入见记录。引脚条件保持不变。`;return snapshot();};
    const pinTest = () => {
      if(m.instruction!=='EXTEST'){m.pinExpected=null;m.pinActual=null;m.pinResult='未执行：需先通过 IR Update 加载 EXTEST';}
      else {m.pinExpected=m.pinStimulus;m.pinActual=m.pinFault==='open'?0:m.pinFault==='short'?1:m.pinStimulus;m.pinResult=m.pinActual===m.pinExpected?`未检出：期望 ${m.pinExpected}，实际 ${m.pinActual}`:`检出差异：期望 ${m.pinExpected}，实际 ${m.pinActual}`;}
      m.action='独立引脚比较，不推进 TCK 或自动执行 DR 扫描';return snapshot();
    };
    return {reset,step,loadInstruction,pinTest,getHistory:()=>copy(history),transitionsFor:state=>({...transitions[state]}),setTdi:value=>{m.tdi=bitValue(value);return snapshot();},setPendingInstruction:value=>{m.pending=Object.prototype.hasOwnProperty.call(instructionBits,value)?value:"BYPASS";return snapshot();},setPinStimulus:value=>{const next=bitValue(value);if(next!==m.pinStimulus)clearPin();m.pinStimulus=next;return snapshot();},setPinFault:value=>{const next=["none","open","short"].includes(value)?value:"none";if(next!==m.pinFault)clearPin();m.pinFault=next;return snapshot();},snapshot};
  }

  function ijtag() {
    const lengths={bist:8,sensor:4},names={bist:"Memory BIST",sensor:"温度传感器"};
    const m={activeSib:0,stagedSib:0,instrument:"bist",instrumentShift:Array(8).fill(0),instrumentValue:Array(8).fill(0),tdi:1,tdo:null,event:"等待操作"};
    const chain=()=>[m.stagedSib,...(m.activeSib?m.instrumentShift:[])];
    const snapshot=()=>({sib:m.activeSib,stagedSib:m.stagedSib,instrument:m.instrument,instrumentName:names[m.instrument],length:1+(m.activeSib?lengths[m.instrument]:0),tdi:m.tdi,tdo:m.tdo,chain:chain(),shifted:chain().join(""),instrumentShift:m.instrumentShift.slice(),instrumentValue:m.activeSib?m.instrumentValue.join(""):"不可见",event:m.event});
    const reset=()=>{m.activeSib=0;m.stagedSib=0;m.instrument="bist";m.instrumentShift=Array(8).fill(0);m.instrumentValue=Array(8).fill(0);m.tdi=1;m.tdo=null;m.event="路径已重置；SIB 尚未更新";return snapshot();};
    const setInstrument=value=>{m.instrument=value==="sensor"?"sensor":"bist";m.instrumentShift=Array(lengths[m.instrument]).fill(0);m.instrumentValue=Array(lengths[m.instrument]).fill(0);m.stagedSib=0;m.event="已选择目标仪器，等待 Shift/Update";return snapshot();};
    const setBit=value=>{m.tdi=value==="0"?0:1;return snapshot();};
    const shift=()=>{const full=chain();m.tdo=full.length?full.pop():0;full.unshift(m.tdi);m.stagedSib=full[0]||0;if(m.activeSib)m.instrumentShift=full.slice(1);m.event=`Shift 完整当前路径：SIB 待读值 ${m.stagedSib}`;return snapshot();};
    const updateSib=()=>{m.activeSib=m.stagedSib;m.event=`Update SIB：路径${m.activeSib?"已打开":"已关闭"}`;return snapshot();};
    const updateInstrument=()=>{if(m.activeSib){m.instrumentValue=m.instrumentShift.slice();m.event="Update 仪器值：已提交当前仪器段";}else m.event="仪器段不可见：先 Update SIB=1";return snapshot();};
    return {reset,setInstrument,setBit,shift,updateSib,updateInstrument,snapshot};
  }

  function wrapper() {
    const m={mode:"internal",input:0,linkMode:"normal",applied:false,coreInput:null,coreOutput:null,externalDrive:null,neighbor:null,internalCell:null,externalCell:null,bypassReg:null,output:null};
    const labels={internal:"Internal Test",external:"External Test",bypass:"Bypass"};
    const clear=()=>{m.applied=false;m.coreInput=m.coreOutput=m.externalDrive=m.neighbor=m.internalCell=m.externalCell=m.bypassReg=m.output=null;};
    const snapshot=()=>({mode:m.mode,modeName:labels[m.mode],input:m.input,linkMode:m.linkMode,applied:m.applied,coreInput:m.coreInput,coreOutput:m.coreOutput,output:m.output,externalDrive:m.externalDrive,neighbor:m.neighbor,internalCell:m.internalCell,externalCell:m.externalCell,bypassReg:m.bypassReg,isolation:m.mode==="internal"?"外部边界隔离":m.mode==="external"?"核心逻辑隔离，仅观察互连":"核心完全旁路",isolated:m.mode!=="external"});
    const reset=()=>{Object.assign(m,{mode:"internal",input:0,linkMode:"normal"});clear();return snapshot();};
    const apply=()=>{clear();m.applied=true;if(m.mode==="internal"){m.internalCell=m.input;m.coreInput=m.input;m.coreOutput=1-m.coreInput;m.output=m.coreOutput;m.externalCell="隔离";}else if(m.mode==="external"){m.externalCell=m.input;m.externalDrive=m.input;m.neighbor=m.linkMode==="invert"?1-m.input:m.linkMode==="stuck0"?0:m.linkMode==="stuck1"?1:m.input;m.output=m.neighbor;m.internalCell="隔离";}else{m.bypassReg=m.input;m.output=m.bypassReg;m.internalCell="旁路";m.externalCell="旁路";}return snapshot();};
    return {reset,apply,setMode:value=>{m.mode=["internal","external","bypass"].includes(value)?value:"internal";clear();return snapshot();},setInput:value=>{m.input=bitValue(value);clear();return snapshot();},setLinkMode:value=>{m.linkMode=["normal","invert","stuck0","stuck1"].includes(value)?value:"normal";clear();return snapshot();},snapshot};
  }

  const API={accessJtag:jtag,accessIjtag:ijtag,accessWrapper:wrapper};globalThis.DFTLabModels=Object.assign(globalThis.DFTLabModels||{},API);
  function text(root,key,value){root.querySelectorAll(`[data-access-field="${key}"]`).forEach(node=>{node.textContent=String(value);});}
  function enable(root){root.querySelectorAll("button,select").forEach(node=>{node.disabled=false;});}
  function bindJtag(root) {
    const model=jtag(),tdi=root.querySelector('[data-access-setting="tdi"]'),instruction=root.querySelector('[data-access-setting="instruction"]'),stim=root.querySelector('[data-access-setting="pin-stimulus"]'),fault=root.querySelector('[data-access-setting="pin-fault"]');
    let viewed=null,inspected='Test-Logic-Reset';
    const stateHelp=state=>state.startsWith('Capture')?'下一上升沿把并行值装入移位寄存器，不等于已提交输出。':state.startsWith('Shift')?'下一上升沿移出旧最低位并移入 TDI；即使 TMS=1 离开 Shift，这一拍仍移一位。':state.startsWith('Update')?'进入此状态的同一拍下降沿提交；不是再等离开状态后的上升沿。':state.startsWith('Pause')?'暂停移位，保存当前移位寄存器；TMS=1 先到 Exit2，再选择继续或提交。':state==='Test-Logic-Reset'?'本模型选择 BYPASS；真实器件的复位指令与 IDCODE 支持以 BSDL 为准。':'只按 TMS 决定下一状态，本状态本身不移动寄存器位。';
    function explainNode(){
      const next=model.transitionsFor(inspected);
      text(root,'node-detail',`${inspected}：TMS=0 → ${next[0]}；TMS=1 → ${next[1]}。${stateHelp(inspected)} 点击节点只查看说明，不跳转 TAP。`);
      root.querySelectorAll('[data-tap-state]').forEach(node=>node.setAttribute('aria-pressed',String(node.dataset.tapState===inspected)));
    }
    function render(record=null) {
      viewed=record;const live=model.snapshot(),s=record?record.after:live;
      root.dataset.liveCycle=String(live.cycles);root.dataset.viewCycle=String(s.cycles);
      text(root,'state',s.state);text(root,'cycles',s.cycles);text(root,'active-path',s.path);text(root,'instruction',s.instruction);
      text(root,'tdi',s.tdi);text(root,'tdo',s.tdo===null?'—':s.tdo);text(root,'scan-bits',s.bits.length?s.bits.join(''):'—');text(root,'pin-result',s.pinResult);
      text(root,'hint',`TMS=0 → ${s.nextStates[0]}；TMS=1 → ${s.nextStates[1]}`);
      text(root,'explanation',record?`第 ${record.cycle} 拍：${record.before.state} → ${s.state}。↑ ${record.rising}；↓ ${record.falling}。`:`${s.action}。每次按钮执行完整 ↑/↓ 一拍；TDO 显示本拍从旧移位寄存器采出的位。`);
      text(root,'view-status',record?`回看第 ${s.cycles} 拍；实际已到第 ${live.cycles} 拍。下一次操作从最新状态继续，不改写历史。`:`当前第 ${live.cycles} 拍。可以选择已记录的 TCK 拍回看。`);
      root.querySelectorAll('[data-tap-state]').forEach(node=>node.classList.toggle('is-active',node.dataset.tapState===s.state));
      root.querySelectorAll('[data-tck]').forEach(button=>button.setAttribute('aria-pressed',String(Number(button.dataset.tck)===s.cycles)));
      root.querySelector('[data-access-action="latest"]').disabled=!record;
      // Controls always edit the live configuration, never a historical snapshot.
      tdi.value=String(live.tdi);instruction.value=live.pending;stim.value=String(live.pinStimulus);fault.value=live.pinFault;
      explainNode();
    }
    function recordHistory(){
      const body=root.querySelector('[data-tck-history]');body.replaceChildren();
      model.getHistory().forEach(record=>{
        const tr=document.createElement('tr'),th=document.createElement('th'),button=document.createElement('button');
        th.scope='row';button.type='button';button.dataset.tck=String(record.cycle);button.textContent=record.cycle;button.setAttribute('aria-label',`查看第 ${record.cycle} 拍`);
        button.addEventListener('click',()=>{render(record);});th.append(button);tr.append(th);
        [record.tms,record.tdi,record.tdo===null?'—':record.tdo,record.before.state+' → '+record.after.state,(record.before.bits.join('')||'—')+' → '+(record.after.bits.join('')||'—'),record.before.instruction+' → '+record.after.instruction,record.falling].forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.append(td);});
        body.append(tr);
      });
    }
    function apply(action){action();recordHistory();render();}
    enable(root);
    root.querySelector('[data-access-action="reset"]').onclick=()=>apply(()=>model.reset());
    root.querySelector('[data-access-action="tms0"]').onclick=()=>apply(()=>model.step(0,tdi.value));
    root.querySelector('[data-access-action="tms1"]').onclick=()=>apply(()=>model.step(1,tdi.value));
    root.querySelector('[data-access-action="load-instruction"]').onclick=()=>apply(()=>model.loadInstruction(instruction.value));
    root.querySelector('[data-access-action="pin-test"]').onclick=()=>apply(()=>{model.setPinStimulus(stim.value);model.setPinFault(fault.value);model.pinTest();});
    root.querySelector('[data-access-action="latest"]').onclick=()=>render();
    tdi.onchange=()=>{model.setTdi(tdi.value);render();};instruction.onchange=()=>{model.setPendingInstruction(instruction.value);render();};
    stim.onchange=()=>{model.setPinStimulus(stim.value);render();};fault.onchange=()=>{model.setPinFault(fault.value);render();};
    root.querySelectorAll('[data-tap-state]').forEach(node=>{
      node.setAttribute('role','button');node.tabIndex=0;
      const routes=model.transitionsFor(node.dataset.tapState),label=document.createElement('small');
      label.textContent=`0 → ${routes[0]} · 1 → ${routes[1]}`;node.append(label);
      const select=()=>{inspected=node.dataset.tapState;explainNode();};
      node.addEventListener('click',select);node.addEventListener('keydown',event=>{if(['Enter',' '].includes(event.key)){event.preventDefault();select();}});
    });
    render();
  }
  function bindIjtag(root){const model=ijtag(),instrument=root.querySelector('[data-access-setting="instrument"]'),bit=root.querySelector('[data-access-setting="bit"]');const render=()=>{const s=model.snapshot();text(root,"sib",`${s.sib?"打开":"关闭"} / 待读 ${s.stagedSib}`);text(root,"instrument",s.instrumentName);text(root,"length",`${s.length} bit`);text(root,"range",s.sib?`${s.length} bit（含 SIB + 仪器段）`:"1 bit（仅 SIB，仪器段旁路）");text(root,"shifted",s.chain.join("")||"—");text(root,"instrument-value",s.instrumentValue);text(root,"event",s.event);text(root,"explanation",s.event+"。Shift 只改变移位寄存器，Update 才提交 SIB 或仪器值。");root.querySelector('[data-access-field="instrument-box"]').textContent=s.sib?s.instrumentName:"旁路";instrument.value=s.instrument;bit.value=String(s.tdi);};enable(root);root.querySelector('[data-access-action="reset"]').onclick=()=>{model.reset();render();};root.querySelector('[data-access-action="shift-sib"]').onclick=()=>{model.shift();render();};root.querySelector('[data-access-action="update-sib"]').onclick=()=>{model.updateSib();render();};root.querySelector('[data-access-action="shift"]').onclick=()=>{model.shift();render();};root.querySelector('[data-access-action="update-instrument"]').onclick=()=>{model.updateInstrument();render();};instrument.onchange=()=>{model.setInstrument(instrument.value);render();};bit.onchange=()=>{model.setBit(bit.value);render();};render();}
  function bindWrapper(root){const model=wrapper(),mode=root.querySelector('[data-access-setting="mode"]'),input=root.querySelector('[data-access-setting="input"]'),link=root.querySelector('[data-access-setting="link"]');const render=()=>{const s=model.snapshot();text(root,"mode",s.modeName);text(root,"input",s.input);text(root,"core",s.coreOutput===null?"—":s.coreOutput);text(root,"core-input",s.coreInput===null?"输入 —":`输入 ${s.coreInput}`);text(root,"external-cell",s.externalCell===null?"—":s.externalCell);text(root,"internal-cell",s.internalCell===null?"—":s.internalCell);text(root,"output",s.output===null?"—":s.output);text(root,"neighbor",s.neighbor===null?"—":s.neighbor);text(root,"bypass-reg",s.bypassReg===null?"—":s.bypassReg);text(root,"isolation",s.isolation);text(root,"result",s.applied?`已应用：输出 ${s.output===null?"—":s.output}`:"尚未应用");text(root,"explanation",s.mode==="internal"?"Internal Test：输入经内测角色进入反相 CORE，外部边界被隔离。":s.mode==="external"?"External Test：只在边界 Cell 捕获外部互连响应，核心逻辑被隔离，不计算 CORE 输出。":"Bypass：输入先锁存到旁路寄存器，核心不参与计算。每种模式复用了同一逻辑边界 Cell 的不同控制角色。");root.querySelectorAll("[data-wrapper-row]").forEach(n=>n.classList.toggle("is-active",n.dataset.wrapperRow===s.mode));mode.value=s.mode;input.value=String(s.input);link.value=s.linkMode;};enable(root);root.querySelector('[data-access-action="reset"]').onclick=()=>{model.reset();render();};root.querySelector('[data-access-action="apply"]').onclick=()=>{model.apply();render();};mode.onchange=()=>{model.setMode(mode.value);render();};input.onchange=()=>{model.setInput(input.value);render();};link.onchange=()=>{model.setLinkMode(link.value);render();};render();}
  function boot(){if(typeof document==="undefined")return;const j=document.querySelector("[data-lab='access-jtag']"),i=document.querySelector("[data-lab='access-ijtag']"),w=document.querySelector("[data-lab='access-wrapper']");if(j)bindJtag(j);if(i)bindIjtag(i);if(w)bindWrapper(w);}
  if(typeof document!=="undefined"){if(document.readyState==="loading")document.addEventListener("DOMContentLoaded",boot,{once:true});else boot();}if(typeof module!=="undefined"&&module.exports)module.exports=API;
})();

