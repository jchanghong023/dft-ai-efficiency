(function (global) {
  'use strict';
  const titles = {'broken-chain':'链路移位异常','reset-constraint':'复位约束不完整','x-source':'捕获响应出现 X','capture-timing':'高速捕获失败'};
  const defaults = {
    'broken-chain':{link:'open',stimulus:'1011'},
    'reset-constraint':{documented:'no',release:3},
    'x-source':{source:'X',mask:'no',fault:'no'},
    'capture-timing':{delay:12,period:10,setup:1,pulses:2}
  };
  const copy = value => JSON.parse(JSON.stringify(value));
  function choice(value, allowed, name) { if (!allowed.includes(value)) throw new Error('无效参数：'+name); return value; }
  function number(value, min, max, name) {
    if ((typeof value !== 'number' && typeof value !== 'string') || String(value).trim() === '') throw new Error('无效参数：'+name);
    const result = Number(value);
    if (!Number.isFinite(result) || result < min || result > max) throw new Error('参数越界：'+name);
    return result;
  }
  function check(title, prompt, issue, result, evidence, next) { return {title,prompt,issue,result,evidence,next,checked:false}; }
  function shift(stimulus, link) {
    let q=[0,0,0,0], output='', trace=[];
    for(let edge=1;edge<=8;edge++) {
      const si=edge<=4?Number(stimulus[edge-1]):0, before=[...q], so=q[3];
      q=[si,q[0],link==='open'?0:q[1],q[2]];
      if(edge>4)output+=so;
      trace.push([edge,edge<=4?'移入':'移出',si,so,before.join(''),q.join(''),output||'—']);
    }
    return {output,trace};
  }
  function simulate(key, settings={}) {
    if (!Object.hasOwn(titles,key)) throw new Error('未知排障场景');
    const p=Object.assign({},defaults[key],settings);
    let topology, columns, trace, checks;
    if(key==='broken-chain') {
      choice(p.link,['normal','open'],'link'); choice(p.stimulus,['0000','1011','1111'],'stimulus');
      const run=shift(p.stimulus,p.link), probe=shift('1111',p.link), mismatch=run.output!==p.stimulus;
      topology='SI → Q1 → Q2 '+(p.link==='open'?'─×─（Q3 扫描输入固定为 0）':'→')+' Q3 → Q4 → SO';
      columns=['沿','阶段','SI','SO 采出','沿前 Q','沿后 Q','累计响应'];trace=run.trace;
      checks=[
        check('检查连接条件','直接检查本模型 Q2→Q3 的扫描连接。',p.link==='open',p.link==='open'?'结构异常：Q3 的扫描输入固定为 0':'本模型扫描连接完整',topology,'执行当前输入的移入和移出。'),
        check('计算当前响应','初值 0000，移入四位再补零移出四位。',mismatch,`期望 ${p.stimulus}，实际 ${run.output}`,mismatch?'当前输入观察到响应差异。':'当前响应一致；零刺激可能无法激活断点，不等于结构无故障。','使用全 1 诊断刺激检查是否被当前输入掩盖。'),
        check('交叉检查激励','另行计算全 1 刺激，不修改上面的当前输入记录。',probe.output!=='1111',`全 1 诊断：期望 1111，实际 ${probe.output}`,probe.output!=='1111'?'全 1 响应也异常，与本模型连接断点相符。':'全 1 响应一致；仅排除本模型的固定零断点，不能排除其他故障。','改变连接或输入重新取证；真实项目另查结构报告。')
      ];
    } else if(key==='reset-constraint') {
      choice(p.documented,['yes','no'],'documented');p.release=number(p.release,0,3,'release');
      if(!Number.isInteger(p.release))throw new Error('释放沿必须为整数');
      let q=[0,0];trace=[];
      for(let edge=1;edge<=2;edge++) {
        const reset=edge<p.release,before=q.join('');q=[1,reset?0:1];
        trace.push([edge,reset?1:0,'11',before,q.join('')]);
      }
      const mismatch=q.join('')!=='11';
      topology='D_A=1 → FF_A（复位已释放） | D_B=1 → FF_B（高有效同步复位）';
      columns=['沿','RST_B','功能 D_A D_B','沿前 Q_A Q_B','沿后 Q_A Q_B'];
      checks=[
        check('区分约束与电路','约束记录是否完整，不改变本模型的真实复位条件。',p.documented==='no',p.documented==='no'?'约束记录缺失':'约束已记录',`配置的 B 域复位在第 ${p.release} 沿之前释放；文档状态不会自动改变电路。`,'观察第 2 沿捕获时的实际复位值。'),
        check('计算捕获响应','第 2 沿检查两个域的同步复位优先级。',mismatch,`第 2 沿期望 11，实际 ${q.join('')}`,mismatch?'B 域仍处于复位，D=1 没有被捕获。':'两域都捕获到 1；约束资料是否齐备仍须独立检查。','把释放沿改为 1 并重新计算，区分控制问题与资料缺口。'),
        check('比较解除复位的反事实','只比较本模型在第 1 沿之前释放时的同步行为。',false,'若第 1 沿前释放，则第 2 沿响应为 11',mismatch?'与当前响应不同，复位控制是本模型中的因果条件。':'与当前响应相同；缺文档不能单独证明存在复位故障。','异步复位的 recovery/removal、CDC 与真实约束另行验证。')
      ];
    } else if(key==='x-source') {
      choice(p.source,['X','0','1'],'source');choice(p.mask,['yes','no'],'mask');choice(p.fault,['yes','no'],'fault');
      const good=p.source==='X'?'X':String(1^Number(p.source));
      const actual=p.source==='X'?'X':String((p.fault==='yes'?0:1)^Number(p.source));
      const status=p.mask==='yes'?'masked':actual==='X'?'unknown':actual===good?'same':'different';
      topology=`A=${p.fault==='yes'?0:1}（无故障 A=1） XOR B=${p.source} → 响应 ${actual} → ${p.mask==='yes'?'屏蔽比较':'参与比较'}`;
      columns=['位置','无故障值','实际值','说明'];trace=[['A','1',p.fault==='yes'?'0':'1','可注入 A stuck-at-0'],['B',p.source,p.source,'X 表示模型未知，不等于物理电平'],['XOR',good,actual,'任何已知位 XOR X 均为 X'],['比较',good,p.mask==='yes'?'—':actual,status]];
      checks=[
        check('追踪未知值来源','先观察比较点之前的原始响应。',p.source==='X',`源 B=${p.source}，原始响应=${actual}`,p.source==='X'?'X 从 B 传播到 XOR 输出。':'B 已知，可继续比较故障与无故障响应。','检查屏蔽是否丢失这一个观察点。'),
        check('计算可比较性','mask 只禁止比较，不会把 X 变为已知，也不会修复故障。',status==='masked'||status==='unknown',status==='masked'?'已屏蔽：本观察点无结论':status==='unknown'?'响应未知：无法判断是否一致':'该观察点可以比较',`原始值 ${actual}；比较状态 ${status}。`,'区分检出、未激活与无观察结论。'),
        check('比较两种电路响应','依据同一组输入比较无故障与实际响应。',status!=='same',status==='different'?'响应不同：观察到示例故障':status==='same'?'本观察点响应一致':'无法判定，不能报告测试通过',`无故障 ${good}，实际 ${actual}；${p.mask==='yes'?'屏蔽丢失了观察能力。':'仅对本模型此观察点有效。'}`,'修改源值、故障或 mask 后重新取证。')
      ];
    } else {
      p.delay=number(p.delay,0,100,'delay');p.period=number(p.period,0.1,100,'period');p.setup=number(p.setup,0,100,'setup');
      p.pulses=number(p.pulses,1,2,'pulses');if(!Number.isInteger(p.pulses))throw new Error('脉冲数必须为整数');
      const deadline=p.period-p.setup,slack=Number((deadline-p.delay).toFixed(4)), enough=p.pulses===2;
      topology=`Launch @ 0 ns → 数据路径 ${p.delay} ns → Capture ${enough?'@ '+p.period+' ns':'缺失'}`;
      columns=['事件','时间 / ns','状态'];trace=[['Launch',0,'数据从 0 翻转为 1'],['数据到达',p.delay,'采样端的理想数据变为 1'],['Setup 截止',Number(deadline.toFixed(4)),'要求此前到达'],['Capture',enough?p.period:'—',enough?(slack>=0?'满足本模型 setup 条件':'setup 违例，采样值不作确定推断'):'没有捕获沿']];
      checks=[
        check('核对脉冲协议','本例必须有一次 launch 和一次 capture。',!enough,`${p.pulses} 个脉冲：${enough?'launch/capture 齐备':'缺少 capture'}`,topology,'协议条件与数据路径裕量分别检查。'),
        check('计算 setup 裕量','裕量 = capture 周期 − setup 要求 − 数据延迟。',slack<0,`setup 裕量 ${slack} ns`,`截止 ${Number(deadline.toFixed(4))} ns，数据 ${p.delay} ns 到达；不包含 skew、hold 或实际库时序弧。`,'确认协议和裕量同时成立，再判断此教学条件。'),
        check('合并条件而非猜采样值','缺脉冲或 setup 违例时，不把采样结果硬编码为 0 或 1。',!enough||slack<0,!enough?'缺捕获沿，未完成测试':slack<0?'时序条件不满足，采样结果不确定':'本模型协议与 setup 条件满足',`脉冲齐备=${enough}；setup 裕量=${slack} ns。不是实际门级仿真或签核结果。`,'调整周期、延迟或脉冲数，重新计算证据。')
      ];
    }
    return {config:p,topology,columns,trace,checks};
  }
  function createModel(key,settings={}) {
    let data=simulate(key,settings),cursor=0;
    function state() {
      return copy({symptom:key,title:titles[key],cursor,total:data.checks.length,
        checked:data.checks.filter(item=>item.checked).length,current:data.checks[cursor]||null,
        done:cursor>=data.checks.length,issues:data.checks.filter(item=>item.checked&&item.issue).length,
        records:data.checks.filter(item=>item.checked),experiment:{config:data.config,topology:data.topology,columns:data.columns,trace:data.trace}});
    }
    return {getState:state,
      inspect() {
        const item=data.checks[cursor];if(!item)return {type:'done',state:state()};
        item.checked=true;return {type:item.issue?'attention':'pass',state:state(),result:item.result,evidence:item.evidence,next:item.next};
      },
      next() {
        const item=data.checks[cursor];if(!item||!item.checked)return {type:'blocked',reason:'先检查当前证据',state:state()};
        cursor++;return {type:cursor>=data.checks.length?'complete':'ready',state:state()};
      },
      reset() {data=simulate(key,data.config);cursor=0;return state();},
      configure(settings) {const next=simulate(key,settings);data=next;cursor=0;return state();}
    };
  }
  global.DFTLabModels=global.DFTLabModels||{};
  global.DFTLabModels.flow={version:2,symptoms:Object.keys(titles).map(key=>({key,title:titles[key]})),createModel,simulate};
  function mount() {
    if(typeof document==='undefined')return;
    const root=document.querySelector('#flow-lab');if(!root)return;
    const setting=root.querySelector('[data-setting="symptom"]');let model;
    const field=(name,value)=>root.querySelectorAll('[data-field="'+name+'"]').forEach(node=>{node.textContent=value;});
    function render(message,explanation) {
      const s=model.getState(),item=s.current;
      field('stage',item?item.title:'已完成取证');field('progress',s.checked+' / '+s.total);
      field('check-title',item?item.title:'检查已结束，不等于问题已解决');field('check-prompt',item?item.prompt:'改变条件重新计算；保留真实项目的报告、约束和波形。');
      field('confirmed',s.checked);field('remaining',s.total-s.checked);field('next-step',item?item.next:'回到真实工程验证');
      field('result',message||'尚未检查');field('confidence',s.done?(s.issues?'仍有异常 / 缺口':'教学检查结束'):'待取证 '+s.checked+'/'+s.total);
      field('explanation',explanation||(s.done?`已检查 ${s.checked} 项，其中 ${s.issues} 项存在异常或无法判定。取证结束不等于修复或签核通过。`:'条件变化会清除旧结论；下表为本组输入的计算预览，点击检查后记录证据。'));
      field('topology',s.experiment.topology);field('evidence-icon',s.issues?'!':s.checked?'✓':'?');
      root.dataset.progress=String(s.checked);root.dataset.state=s.done?(s.issues?'attention':'complete'):'ready';
      root.querySelector('[data-action="next"]').disabled=!item||!item.checked;root.querySelector('[data-action="inspect"]').disabled=!item;
      const head=root.querySelector('[data-trace-head]'),body=root.querySelector('[data-trace-body]');head.replaceChildren();body.replaceChildren();
      s.experiment.columns.forEach(label=>{const th=document.createElement('th');th.scope='col';th.textContent=label;head.append(th);});
      s.experiment.trace.forEach(values=>{const tr=document.createElement('tr');values.forEach(value=>{const td=document.createElement('td');td.textContent=value;tr.append(td);});body.append(tr);});
      const records=root.querySelector('[data-evidence-records]');records.replaceChildren();
      s.records.forEach(record=>{const li=document.createElement('li');li.textContent=record.title+'：'+record.result+'；'+record.evidence;records.append(li);});
    }
    function reset() {
      const settings={};
      root.querySelectorAll('[data-flow-options]').forEach(group=>{
        group.hidden=group.dataset.flowOptions!==setting.value;
        if(!group.hidden)group.querySelectorAll('[data-parameter]').forEach(input=>{settings[input.dataset.parameter]=input.value;});
      });
      model=createModel(setting.value,settings);render();
    }
    root.querySelectorAll('button, select').forEach(node=>{node.disabled=false;});
    root.querySelector('[data-action="inspect"]').addEventListener('click',()=>{const r=model.inspect();render(r.result,r.evidence);});
    root.querySelector('[data-action="next"]').addEventListener('click',()=>{const r=model.next();render(r.type==='complete'?'本轮取证结束':'继续检查下一项');});
    root.querySelector('[data-action="reset"]').addEventListener('click',reset);
    root.querySelectorAll('[data-parameter]').forEach(input=>input.addEventListener('change',reset));
    setting.addEventListener('change',reset);reset();
  }
  if(typeof document!=='undefined'){if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',mount);else mount();}
})(typeof globalThis!=='undefined'?globalThis:this);
