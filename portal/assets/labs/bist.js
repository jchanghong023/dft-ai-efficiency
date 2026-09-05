"use strict";
/*
 * The two models below are deliberately small, deterministic teaching models.
 * They are also usable from Node without a DOM: tests load this file and call
 * globalThis.DFTLabModels.bistMemory / bistLogic directly.
 */
(() => {
  const rootGlobal = typeof globalThis !== "undefined" ? globalThis : this;
  const models = rootGlobal.DFTLabModels = rootGlobal.DFTLabModels || {};

  const range = (count, direction) => {
    const result = [];
    if (direction === "down") for (let i = count - 1; i >= 0; i--) result.push(i);
    else for (let i = 0; i < count; i++) result.push(i);
    return result;
  };
  const expandMarch = rows => {
    const phases = [
      ["↑ W0", "up", [["w", 0]]],
      ["↑ R0/W1", "up", [["r", 0], ["w", 1]]],
      ["↓ R1/W0", "down", [["r", 1], ["w", 0]]],
      ["↓ R0", "down", [["r", 0]]]
    ];
    return phases.flatMap(([label, direction, actions]) => range(rows, direction).flatMap(address =>
      actions.map(([op, value]) => ({ phase: label, direction, address, op, value }))));
  };

  function createMemory(options = {}) {
    const rows = Number.isInteger(options.rows) && options.rows > 0 ? options.rows : 8;
    const spareRows = Number.isInteger(options.spareRows) && options.spareRows >= 0 ? options.spareRows : 1;
    let faultAddresses = [];
    let base = [], spare = [], mapping = {};
    const state = { phase: "test", cursor: 0, total: 0, failures: [], verificationFailures: [], mapping: {}, candidateMapping: {}, unrepairable: [], rowValues: [], last: null, result: "pending" };
    const faultList = value => value === "two" ? [3, 6] : value === "none" ? [] : [3];
    const physical = address => Object.prototype.hasOwnProperty.call(mapping, address) ? mapping[address] : address;
    const read = address => {
      const p = physical(address);
      if (faultAddresses.includes(p)) return 1;
      return p < rows ? base[p] : spare[p - rows] || 0;
    };
    const write = (address, value) => {
      const p = physical(address);
      if (p < rows) base[p] = value ? 1 : 0;
      else spare[p - rows] = value ? 1 : 0;
    };
    const reset = fault => {
      faultAddresses = faultList(fault); base = Array(rows).fill(0); spare = Array(spareRows).fill(0); mapping = {};
      state.phase = "test"; state.cursor = 0; state.total = expandMarch(rows).length; state.failures = []; state.verificationFailures = []; state.mapping = {}; state.candidateMapping = {}; state.unrepairable = []; state.rowValues = [...base]; state.last = null; state.result = "pending";
      return state;
    };
    const execute = (item, verification) => {
      let actual = null, mismatch = false;
      if (item.op === "w") write(item.address, item.value);
      else { actual = read(item.address); mismatch = actual !== item.value; }
      state.rowValues[item.address] = read(item.address);
      const event = { ...item, actual, mismatch, verification: Boolean(verification) };
      state.last = event;
      const list = verification ? state.verificationFailures : state.failures;
      if (mismatch) list.push({ address: item.address, expected: item.value, actual });
      state.cursor += 1;
      return event;
    };
    const testOps = () => expandMarch(rows);
    const verifyOps = () => range(rows, "up").flatMap(address => [["w", 0], ["r", 0], ["w", 1], ["r", 1]].map(([op, value]) => ({ phase: "VERIFY", direction: "up", address, op, value })));
    const step = () => {
      if (state.phase === "test") {
        const event = execute(testOps()[state.cursor]);
        if (state.cursor >= state.total) state.phase = "bira-ready";
        return event;
      }
      if (state.phase === "verify") {
        const ops = verifyOps(), event = execute(ops[state.cursor], true);
        if (state.cursor >= state.total) { state.phase = "done"; state.result = state.verificationFailures.length ? "fail" : "pass"; }
        return event;
      }
      return null;
    };
    const analyze = () => {
      if (state.phase !== "bira-ready") return { mapping: { ...state.mapping }, unrepairable: [...state.unrepairable] };
      const failed = [...new Set(state.failures.map(item => item.address))];
      mapping = {}; state.unrepairable = [];
      failed.forEach((address, index) => {
        if (index < spareRows) mapping[address] = rows + index;
        else state.unrepairable.push(address);
      });
      state.candidateMapping = { ...mapping }; state.phase = "bira-done";
      return { mapping: { ...state.candidateMapping }, unrepairable: [...state.unrepairable] };
    };
    const applyRepair = () => {
      if (state.phase !== "bira-done") return false;
      mapping = { ...state.candidateMapping }; state.mapping = { ...mapping };
      state.phase = "verify"; state.cursor = 0; state.total = verifyOps().length; state.verificationFailures = []; state.result = "pending";
      return true;
    };
    reset(options.fault || "stuck1");
    return { state, reset, step, analyze, applyRepair, testOps, verifyOps,
      snapshot: () => ({ ...state, failures: state.failures.map(item => ({ ...item })), verificationFailures: state.verificationFailures.map(item => ({ ...item })), mapping: { ...state.mapping }, candidateMapping: { ...state.candidateMapping }, unrepairable: [...state.unrepairable] }) };
  }
  models.bistMemory = { create: createMemory, march: expandMarch };

  const MASK4 = 0b1111;
  const lfsrStep = state => ((state << 1) & MASK4) | (((state >> 3) ^ (state >> 2)) & 1);
  const dutResponse = (stimulus, fault = "none") => {
    let response = (stimulus ^ (stimulus >> 1) ^ ((stimulus << 1) & MASK4)) & MASK4;
    if (fault === "stuck") response &= 0b1101;
    return response;
  };
  const misrStep = (signature, response) => {
    let result = signature & MASK4;
    for (let i = 0; i < 4; i++) {
      const input = (response >> i) & 1;
      const feedback = ((result >> 3) & 1) ^ input;
      result = (result << 1) & MASK4;
      if (feedback) result ^= 0b0011;
    }
    return result;
  };
  const knownSequence = [1, 2, 4, 9, 3, 6, 13, 10];
  const knownResponses = [3, 7, 14, 15, 4, 9, 1, 11];
  const knownSignatures = [7, 8, 2, 4, 10, 5, 4, 8];
  const goldenSignature = (seed = 1, cycles = 8) => { let lfsr = seed, signature = 0; for (let i = 0; i < cycles; i++) { signature = misrStep(signature, dutResponse(lfsr)); lfsr = lfsrStep(lfsr); } return signature; };
  const KNOWN_SIGNATURE = 0b1000;

  function createLogic(options = {}) {
    const cycles = Number.isInteger(options.cycles) && options.cycles > 0 ? options.cycles : 8;
    const seed = Number.isInteger(options.seed) && options.seed !== 0 ? options.seed & MASK4 : 1;
    const expected = seed === 1 && cycles === 8 ? KNOWN_SIGNATURE : goldenSignature(seed, cycles);
    const state = { phase: "ready", cycle: 0, cycles, lfsr: seed, response: 0, signature: 0, expected, result: "pending", history: [] };
    const reset = () => { state.phase = "ready"; state.cycle = 0; state.lfsr = seed; state.response = 0; state.signature = 0; state.expected = expected; state.result = "pending"; state.history = []; return state; };
    const step = fault => {
      if (state.cycle >= cycles) return null;
      const stimulus = state.lfsr, response = dutResponse(stimulus, fault || "none"), before = state.signature;
      state.signature = misrStep(state.signature, response); state.lfsr = lfsrStep(state.lfsr); state.cycle += 1; state.response = response;
      const event = { cycle: state.cycle, stimulus, response, signatureBefore: before, signature: state.signature };
      state.history.push(event);
      if (state.cycle >= cycles) { state.phase = "done"; state.result = state.signature === state.expected ? "pass" : "fail"; }
      else state.phase = "running";
      return event;
    };
    reset();
    return { state, reset, step, lfsrStep, misrStep, dutResponse, knownSequence, knownSignature: KNOWN_SIGNATURE };
  }
  models.bistLogic = { create: createLogic, lfsrStep, misrStep, dutResponse, knownSequence, knownResponses, knownSignatures, knownSignature: KNOWN_SIGNATURE };

  if (typeof document === "undefined") return;
  const bind = (selector, setup) => { const node = document.querySelector(selector); if (node) setup(node); };
  const display = (root, name, value) => root.querySelectorAll(`[data-field="${name}"]`).forEach(node => { node.textContent = value; });
  const stopTimer = (timer, button) => { if (timer.value !== null) clearInterval(timer.value); timer.value = null; if (button) button.textContent = "播放"; };

  bind("#memory-bist-lab", root => {
    let model, timer = { value: null };
    const speed = root.querySelector('[data-setting="speed"]');
    const setting = root.querySelector('[data-setting="fault"]'), stepButton = root.querySelector('[data-action="step"]'), play = root.querySelector('[data-action="play"]');
    const rowDraw = () => { const map = model.state.mapping; for (let i = 0; i < 8; i++) { const node = root.querySelector(`[data-row-value="${i}"]`); if (node) node.textContent = model.state.rowValues[i] ?? 0; const mapNode = root.querySelector(`[data-row-map="${i}"]`); if (mapNode) mapNode.textContent = Object.prototype.hasOwnProperty.call(map, i) ? `S${map[i] - 8}` : "—"; } };
    const update = () => {
      const s = model.state, last = s.last;
      display(root, "phase", s.phase === "test" ? "MBIST · March 测试" : s.phase === "bira-ready" ? "测试完成 · 等待 BIRA" : s.phase === "bira-done" ? "BIRA 完成 · 等待 BISR" : s.phase === "verify" ? "BISR · 验证映射" : s.phase === "done" ? "完成 · 验证结果" : s.phase);
      display(root, "cursor", s.cursor); display(root, "total", s.total); display(root, "address", last ? `A${last.address}` : "—"); display(root, "operation", last ? `${last.op.toUpperCase()} ${last.value} @ A${last.address}` : "等待操作");
      display(root, "readout", last && last.op === "r" ? `${last.actual} / ${last.value}${last.mismatch ? " · FAIL" : " · OK"}` : "写操作 · 等待读回");
      const failed = [...new Set(s.failures.map(item => item.address))]; display(root, "failures", failed.length ? failed.map(address => `A${address}`).join(", ") : "尚无失败"); display(root, "failure-list", failed.length ? failed.map(address => `A${address}`).join(", ") : "—");
      const shownMapping = s.phase === "bira-done" ? s.candidateMapping : s.mapping; display(root, "mapping", Object.keys(shownMapping).length ? Object.entries(shownMapping).map(([address, physical]) => `A${address}→S${physical - 8}`).join(" ") : "—"); display(root, "resource", s.unrepairable.length ? `剩余未修复 A${s.unrepairable.join(",")}` : Object.keys(shownMapping).length ? (s.phase === "bira-done" ? "待 BISR 加载" : "已分配") : "未分配"); display(root, "result", s.result === "pass" ? "PASS · 修复后验证通过" : s.result === "fail" ? "FAIL · spare 不足或仍有失败" : "尚未验证");
      display(root, "explanation", last ? (last.mismatch ? `A${last.address} 读回 ${last.actual}，期望 ${last.value}：记录为失败地址。${s.phase === "bira-ready" ? "现在可以执行 BIRA。" : ""}` : `第 ${s.cursor} 步：${last.op.toUpperCase()} A${last.address}，${last.op === "r" ? "读回值符合期望。" : "已写入模型。"}`) : "先运行 MBIST 的已知 March 序列。发现失败后，再分别执行 BIRA 资源分配和 BISR 映射加载。");
      rowDraw();
      const testDone = s.phase === "bira-ready", analysisDone = s.phase === "bira-done", verifying = s.phase === "verify";
      stepButton.disabled = !(s.phase === "test" || verifying); play.disabled = !(s.phase === "test" || verifying); root.querySelector('[data-action="analyze"]').disabled = !testDone; root.querySelector('[data-action="repair"]').disabled = !analysisDone;
    };
    const reset = () => { stopTimer(timer, play); const selected = setting.value || "stuck1"; setting.value = selected; model = models.bistMemory.create({ fault: selected, rows: 8, spareRows: 1 }); display(root, "spare", "SPARE 0"); update(); };
    const advance = () => { const event = model.step(); if (!event) return; root.dataset.step = String(model.state.cursor); root.classList.remove("tick"); void root.offsetWidth; root.classList.add("tick"); update(); if (model.state.phase === "done" || model.state.phase === "bira-ready") stopTimer(timer, play); };
    root.querySelectorAll("button, select").forEach(node => { node.disabled = false; });
    stepButton.addEventListener("click", () => { stopTimer(timer, play); advance(); }); play.addEventListener("click", () => { if (timer.value !== null) { stopTimer(timer, play); return; } play.textContent = "暂停"; timer.value = setInterval(advance, 420 / Number(speed.value)); }); speed.addEventListener("change", () => { if(timer.value !== null) { clearInterval(timer.value); timer.value = setInterval(advance, 420 / Number(speed.value)); } });
    root.querySelector('[data-action="analyze"]').addEventListener("click", () => { model.analyze(); update(); }); root.querySelector('[data-action="repair"]').addEventListener("click", () => { model.applyRepair(); update(); }); root.querySelector('[data-action="reset"]').addEventListener("click", reset); setting.addEventListener("change", reset); document.addEventListener("visibilitychange", () => { if (document.hidden) stopTimer(timer, play); }); window.addEventListener("pagehide", () => stopTimer(timer, play)); reset();
  });

  bind("#logic-bist-lab", root => {
    let model, timer = { value: null };
    const speed = root.querySelector('[data-setting="speed"]');
    const setting = root.querySelector('[data-setting="fault"]'), stepButton = root.querySelector('[data-action="step"]'), play = root.querySelector('[data-action="play"]');
    const bits = value => value.toString(2).padStart(4, "0");
    const update = () => { const s = model.state, last = s.history[s.history.length - 1]; display(root, "phase", s.phase === "ready" ? "准备产生第一个模式" : s.phase === "done" ? "完成 · 比较签名" : "运行 · 采样并压缩"); display(root, "cycle", s.cycle); display(root, "state", bits(s.lfsr)); display(root, "lfsr", bits(last ? last.stimulus : s.lfsr)); display(root, "response", bits(s.response)); display(root, "misr", bits(s.signature)); display(root, "signature", bits(s.signature)); display(root, "expected", bits(s.expected)); display(root, "pair", last ? `${bits(last.stimulus)} / ${bits(last.response)}` : "尚未执行"); display(root, "result", s.result === "pass" ? `PASS · ${bits(s.signature)} 与期望一致` : s.result === "fail" ? `FAIL · ${bits(s.signature)} 与期望不同` : "尚未完成"); display(root, "explanation", last ? `第 ${s.cycle} 拍：激励 ${bits(last.stimulus)} → 响应 ${bits(last.response)} → MISR ${bits(last.signature)}。${s.phase === "done" ? "这是固定已知序列的末次签名。" : "下一拍使用新的 LFSR 状态。"}` : "这是一个固定 8 拍的教学序列。签名比较只表示本模型、本位序和本组模式的结果，不是 ATPG 覆盖率或量产测试结论。"); stepButton.disabled = s.phase === "done"; play.disabled = s.phase === "done"; };
    const reset = () => { stopTimer(timer, play); const selected = setting.value || "none"; setting.value = selected; model = models.bistLogic.create(); update(); };
    const advance = () => { const event = model.step(setting.value); if (!event) return; root.dataset.step = String(model.state.cycle); root.classList.remove("tick"); void root.offsetWidth; root.classList.add("tick"); update(); if (model.state.phase === "done") stopTimer(timer, play); };
    root.querySelectorAll("button, select").forEach(node => { node.disabled = false; }); stepButton.addEventListener("click", () => { stopTimer(timer, play); advance(); }); play.addEventListener("click", () => { if (timer.value !== null) { stopTimer(timer, play); return; } play.textContent = "暂停"; timer.value = setInterval(advance, 650 / Number(speed.value)); }); speed.addEventListener("change", () => { if(timer.value !== null) { clearInterval(timer.value); timer.value = setInterval(advance, 650 / Number(speed.value)); } }); root.querySelector('[data-action="reset"]').addEventListener("click", reset); setting.addEventListener("change", reset); document.addEventListener("visibilitychange", () => { if (document.hidden) stopTimer(timer, play); }); window.addEventListener("pagehide", () => stopTimer(timer, play)); reset();
  });
})();
