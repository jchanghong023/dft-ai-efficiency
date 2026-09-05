"use strict";
(() => {
  // Pure edge model: rendering and historical selection cannot mutate its state.
  function createScan(options = {}) {
    let stimulus, fault, expected, q, output, events;
    const copy = value => JSON.parse(JSON.stringify(value));
    const functional = state => [state[1] ^ state[3], state[0] & state[2], state[1] | state[2], 1 ^ state[3]];
    const current = () => copy(events[events.length - 1]);
    const reset = (settings = {stimulus, fault}) => {
      const next = settings.stimulus === undefined ? '1011' : settings.stimulus;
      const mode = settings.fault === undefined ? 'none' : settings.fault;
      if (typeof next !== 'string' || !/^[01]{4}$/.test(next)) throw new Error('Scan 刺激必须是四个二进制位');
      if (!['none', 'stuck'].includes(mode)) throw new Error('未知 Scan 故障');
      stimulus = next; fault = mode; q = [0,0,0,0]; output = [];
      expected = functional([...stimulus].reverse().map(Number)).reverse().join('');
      events = [{cycle:0, phase:'ready', se:1, si:Number(stimulus[0]), so:null,
        before:[...q], after:[...q], d:null, output:'', expected, stimulus, fault, done:false, result:''}];
      return current();
    };
    const step = () => {
      if (events.length === 10) return current();
      const cycle = events.length, before = [...q], se = cycle === 5 ? 0 : 1;
      const si = se ? (cycle <= 4 ? Number(stimulus[cycle - 1]) : 0) : null;
      const so = se ? before[3] : null;
      let d = null;
      if (!se) {
        d = functional(before);
        q = [...d];
        if (fault === 'stuck') q[2] = 0;
      } else {
        q = [si, ...before.slice(0,3)];
        if (cycle > 5) output.push(so);
      }
      events.push({cycle, phase:cycle <= 4 ? 'shift-in' : cycle === 5 ? 'capture' : 'shift-out',
        se, si, so, before, after:[...q], d, output:output.join(''), expected, stimulus, fault,
        done:cycle === 9, result:cycle === 9 ? (output.join('') === expected ? 'same' : 'different') : ''});
      return current();
    };
    reset(options);
    return {reset, step, getState:current, getHistory:() => copy(events)};
  }
  const scope = typeof window === 'undefined' ? globalThis : window;
  scope.DFTLabModels = scope.DFTLabModels || {};
  scope.DFTLabModels.scan = {create:createScan};
  if (typeof document === 'undefined') return;

  function controller(root, model) {
    let timer = null;
    const field = (name, value) => { root.querySelectorAll(`[data-field="${name}"]`).forEach(node => { node.textContent = value; }); };
    const play = root.querySelector('[data-action="play"]');
    const stepButton = root.querySelector('[data-action="step"]');
    const speed = root.querySelector('[data-setting="speed"]');
    const setting = root.querySelector('[data-setting="fault"]');
    const stop = () => { if (timer !== null) clearInterval(timer); timer = null; play.textContent = "播放"; };
    const reset = () => { stop(); root.classList.remove("tick"); root.dataset.result = ""; model.reset(setting.value, field); root.dataset.step = "0"; stepButton.disabled = false; play.disabled = false; };
    const advance = () => {
      const done = model.step(field);
      root.dataset.step = String(model.cycle);
      root.classList.remove("tick"); void root.offsetWidth; root.classList.add("tick");
      if (done) { stop(); stepButton.disabled = true; play.disabled = true; }
    };
    root.querySelectorAll("button, select").forEach(node => { node.disabled = false; });
    stepButton.addEventListener("click", () => { stop(); advance(); });
    root.querySelector('[data-action="reset"]').addEventListener("click", reset);
    play.addEventListener("click", () => { if (timer !== null) { stop(); return; } play.textContent = "暂停"; timer = setInterval(advance, 850 / Number(speed.value)); });
    setting.addEventListener("change", reset);
    speed.addEventListener("change", () => { if(timer !== null) { clearInterval(timer); timer = setInterval(advance, 850 / Number(speed.value)); } });
    document.addEventListener("visibilitychange", () => { if (document.hidden) stop(); });
    window.addEventListener("pagehide", stop);
    reset();
  }

  const scan = document.querySelector('#scan-demo');
  if (scan) {
    const model = createScan(), field = (name, value) => scan.querySelectorAll(`[data-field="${name}"]`).forEach(node => { node.textContent = value; });
    const play = scan.querySelector('[data-action="play"]'), step = scan.querySelector('[data-action="step"]');
    const speed = scan.querySelector('[data-setting="speed"]'), fault = scan.querySelector('[data-setting="fault"]');
    const inputs = [...scan.querySelectorAll('[data-stimulus]')], history = scan.querySelector('[data-history]');
    const phaseNames = {ready:'准备移入', 'shift-in':'Shift-in · 移入刺激', capture:'Capture · 捕获响应', 'shift-out':'Shift-out · 移出响应'};
    let timer = null, viewed = model.getState(), component = 'mux';
    const stop = () => { if (timer !== null) clearInterval(timer); timer = null; play.textContent = '播放'; };
    function explain(state) {
      if (!state.cycle) return `输入 ${state.stimulus} 按从左到右的时间顺序移入；四个移位沿后将得到 ${[...state.stimulus].reverse().join('')}。改变输入或故障会重置本轮记录。`;
      if (!state.se) return `SE=0，沿前 Q=${state.before.join('')} 同时决定无故障 D=${state.d.join('')}，沿后 Q=${state.after.join('')}。` +
        (state.fault === 'stuck' ? (state.d[2] ? 'D3 原本应为 1，stuck-at-0 被激活；接下来移出才能观察差异。' : 'D3 原本就是 0，本组刺激没有激活 stuck-at-0，不能由响应一致断言没有故障。') : '四个触发器同时采样，不使用同一沿刚更新的 Q。');
      if (state.done) return `期望 ${state.expected}，实际 ${state.output}。` + (state.result === 'different' ? '这组刺激观察到了 D3 stuck-at-0。' : state.fault === 'stuck' ? '故障仍存在，但本组刺激没有激活它；一致不等于无故障。' : '本组刺激响应一致，不代表覆盖全部故障。');
      return `第 ${state.cycle} 沿：SI=${state.si}，Q 从 ${state.before.join('')} 变为 ${state.after.join('')}；本沿采出的 SO=${state.so} 是沿前 Q4。` + (state.cycle <= 4 ? '尚未捕获功能响应。' : `第 ${state.cycle - 5} 个响应位已读出，补入 0。`);
    }
    function showComponent() {
      const s = viewed, before = s.before.join(''), after = s.after.join('');
      let text;
      if (/^q[0-3]$/.test(component)) {
        const i = Number(component[1]);
        text = `Q${i+1}：${s.before[i]} → ${s.after[i]}。` + (!s.cycle ? '这是初始状态，还没有时钟沿。' : s.se ? `SE=1，本沿采样${i ? `沿前 Q${i}=${s.before[i-1]}` : `SI=${s.si}`}。` : `SE=0，本沿采样功能 D${i+1}=${s.after[i]}${i === 2 && s.fault === 'stuck' ? `（无故障值 ${s.d[i]}，故障固定为 0）` : ''}。`);
      } else if (component === 'logic') text = 'D1=Q2 XOR Q4；D2=Q1 AND Q3；D3=Q2 OR Q3；D4=NOT Q4。' + (s.d ? `本次使用沿前 Q=${before} 得到无故障 D=${s.d.join('')}。` : '只有捕获沿才把功能输出写入寄存器；扫描移位绕过功能 D。');
      else if (component === 'io') text = s.se && s.cycle ? `本沿 SI=${s.si}；采出的 SO=${s.so} 来自沿前 Q4。沿后输出引脚的组合电平已随新 Q4 变为 ${s.after[3]}，不要与本沿采出值混淆。` : 'SI 是串行输入；记录里的 SO 是移位沿采出的旧末级位。准备态或捕获沿不记录 SO 响应位。';
      else if (component === 'clock') text = `本图为上升沿触发的理想同步模型；${s.cycle ? `第 ${s.cycle} 沿让 Q 从 ${before} 同时变为 ${after}` : '尚未执行时钟沿'}。表格的边沿序号不是 ns；高亮和播放速度不是物理传播延迟。`;
      else text = `MUX：SE=${s.se}，选择${s.se ? '扫描输入（Q1 来自 SI，其余来自沿前一级 Q）' : '功能 D'}。选择信号不单独更新触发器；状态只在时钟沿更新。`;
      field('component-detail', text);
      scan.querySelectorAll('[data-inspect]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.inspect === component)));
    }
    function render(state) {
      viewed = state;
      const latest = model.getState();
      scan.dataset.phase = state.se ? 'shift' : 'capture'; scan.dataset.result = state.result;
      scan.dataset.step = String(latest.cycle); scan.dataset.viewStep = String(state.cycle);
      field('cycle', state.cycle); field('phase', state.done ? '完成 · 比较响应' : phaseNames[state.phase]);
      field('se', state.se); field('si', state.si === null ? '—' : state.si); field('so', state.so === null ? '—' : state.so);
      field('registers', state.after.join('')); field('output', state.output || '尚未移出'); field('expected', state.expected);
      field('explanation', explain(state));
      field('view-status', state.cycle === latest.cycle ? `当前第 ${latest.cycle} 沿 · 点击已记录边沿可回看` : `回看第 ${state.cycle} 沿 · 实验已到第 ${latest.cycle} 沿；继续操作从最新状态推进，不改写历史`);
      state.after.forEach((bit, i) => { scan.querySelector(`[data-q="${i}"]`).textContent = bit; });
      history.querySelectorAll('[data-edge]').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.edge) === state.cycle)));
      step.disabled = latest.done; play.disabled = latest.done;
      scan.querySelector('[data-action="latest"]').disabled = state.cycle === latest.cycle;
      showComponent();
    }
    function record() {
      history.replaceChildren();
      for (const event of model.getHistory()) {
        const row = document.createElement('tr'), header = document.createElement('th'), button = document.createElement('button');
        header.scope = 'row'; button.type = 'button'; button.dataset.edge = String(event.cycle);
        button.textContent = event.cycle ? `↑ ${event.cycle}` : '初始'; button.setAttribute('aria-label', `查看${event.cycle ? `第 ${event.cycle} 沿` : '初始状态'}`);
        button.addEventListener('click', () => { stop(); scan.classList.remove('tick'); render(event); });
        header.append(button); row.append(header);
        for (const value of [phaseNames[event.phase],event.se,event.si === null ? '—' : event.si,event.so === null ? '—' : event.so,event.before.join(''),event.after.join(''),event.output || '—']) {
          const cell = document.createElement('td'); cell.textContent = value; row.append(cell);
        }
        history.append(row);
      }
    }
    const advance = () => {
      const state = model.step(); record(); render(state);
      scan.classList.remove('tick'); void scan.offsetWidth; scan.classList.add('tick');
      if (state.done) stop();
    };
    const reset = () => {
      stop(); scan.classList.remove('tick');
      const state = model.reset({stimulus:inputs.map(input => input.value).join(''), fault:fault.value});
      record(); render(state);
    };
    scan.querySelectorAll('button, select').forEach(node => { node.disabled = false; });
    step.addEventListener('click', () => { stop(); advance(); });
    play.addEventListener('click', () => {
      if (timer !== null) { stop(); return; }
      render(model.getState()); play.textContent = '暂停'; timer = setInterval(advance, 850 / Number(speed.value));
    });
    speed.addEventListener('change', () => { if (timer !== null) { clearInterval(timer); timer = setInterval(advance, 850 / Number(speed.value)); } });
    scan.querySelector('[data-action="reset"]').addEventListener('click', reset);
    scan.querySelector('[data-action="latest"]').addEventListener('click', () => { stop(); render(model.getState()); });
    fault.addEventListener('change', reset); inputs.forEach(input => input.addEventListener('change', reset));
    scan.querySelectorAll('[data-inspect]').forEach(button => button.addEventListener('click', () => { component = button.dataset.inspect; showComponent(); }));
    scan.querySelectorAll('[data-component]').forEach(node => {
      node.setAttribute('tabindex', '0'); node.setAttribute('role', 'button');
      const select = () => { component = node.dataset.component; showComponent(); };
      node.addEventListener('click', select); node.addEventListener('keydown', event => { if (['Enter',' '].includes(event.key)) { event.preventDefault(); select(); } });
    });
    document.addEventListener('visibilitychange', () => { if (document.hidden) stop(); });
    window.addEventListener('pagehide', stop);
    reset();
  }

  const edt = document.querySelector('#edt-demo');
  if (edt) {
    const initial = [[1,0,1,0],[0,1,1,0],[1,1,0,1],[0,0,1,1]];
    const stimuli = [[1,0],[0,1],[1,1],[1,0]], expected = ["11", "10", "11", "00"];
    let chains, outputs, fault;
    const draw = () => { chains.forEach((row, r) => row.forEach((value, c) => { edt.querySelector(`[data-edt-q="${r}-${c}"]`).textContent = value; })); };
    const model = {
      cycle: 0,
      reset(value, field) {
        this.cycle = 0; chains = initial.map(row => [...row]); outputs = []; fault = value;
        if (fault !== "none") chains[0][3] ^= 1;
        if (fault === "double") chains[2][3] ^= 1;
        edt.dataset.phase = "shift"; field("cycle", 0); field("phase", "已捕获响应，准备移位"); field("input-a", 1); field("input-b", 0); field("out-c0", "—"); field("out-c1", "—"); field("raw-output", "尚未移出"); field("output", "尚未移出");
        [1,0,1,1].forEach((value, i) => { edt.querySelector(`[data-lane="${i}"]`).textContent = value; });
        field("explanation", "链内已有响应。点击单步，观察四个旧末级位如何变成两个压缩观察位。"); draw();
      },
      step(field) {
        if (this.cycle >= 4) return true;
        const [a,b] = stimuli[this.cycle], inputs = [a,b,a^b,a], raw = chains.map(row => row[3]);
        const compact = [raw[0]^raw[2],raw[1]^raw[3]]; outputs.push(compact.join(""));
        chains = chains.map((row, i) => [inputs[i], ...row.slice(0,3)]); this.cycle++;
        field("cycle", this.cycle); field("phase", this.cycle === 4 ? "完成 · 比较压缩响应" : "Shift · 四条链并行移位");
        field("input-a", a); field("input-b", b); field("out-c0", compact[0]); field("out-c1", compact[1]); field("raw-output", raw.join("")); field("output", outputs.join(" · "));
        inputs.forEach((value, i) => { edt.querySelector(`[data-lane="${i}"]`).textContent = value; }); draw();
        const mismatch = outputs.some((value, i) => value !== expected[i]);
        edt.dataset.result = mismatch ? "different" : fault === "double" ? "alias" : "same";
        field("explanation", `输入 (${a},${b}) 映射为 ${inputs.join("")}，同时装入四条链；旧末级响应 ${raw.join("")} 压缩为 ${compact.join("")}。${mismatch ? "压缩响应与期望不一致，观察到了差异。" : fault === "double" ? "两个错误进入同一 XOR 组并抵消：压缩一致不等于原始响应无错误。" : "当前压缩响应与期望一致。"}`);
        return this.cycle === 4;
      }
    };
    controller(edt, model);
  }
})();
