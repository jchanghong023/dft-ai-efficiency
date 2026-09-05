"use strict";
(() => {
  const coverageExample = Object.freeze({detected: 12, "not-detected": 4, untestable: 2, aborted: 2});
  const patterns = ["00", "01", "10", "11"];

  function validPattern(value) {
    return typeof value === "string" && /^[01]{2}$/.test(value) ? value : "00";
  }
  function bits(pattern) {
    if (typeof pattern === "string") {
      const value = validPattern(pattern);
      return {a: Number(value[0]), b: Number(value[1])};
    }
    const a = pattern && (pattern.a === 1 || pattern.a === true) ? 1 : 0;
    const b = pattern && (pattern.b === 1 || pattern.b === true) ? 1 : 0;
    return {a, b};
  }
  function circuit(pattern) {
    const {a, b} = bits(pattern);
    const n1 = a | b, n2 = a & b;
    return {a, b, n1, n2, out: n1 ^ n2};
  }
  function simulateFault(options) {
    const fault = options && options.fault || "stuck-at-0";
    const good = circuit(options && options.pattern || "10");
    const previous = circuit(options && options.previous || "00");
    const faulty = {...good};
    let activated = false;
    if (fault === "stuck-at-0" || fault === "stuck-at-1") {
      faulty.n1 = fault === "stuck-at-0" ? 0 : 1;
      activated = faulty.n1 !== good.n1;
      faulty.out = faulty.n1 ^ faulty.n2;
    } else if (fault === "bridging") {
      // Teaching abstraction: a dominant-AND bridge forces both inputs to a&b.
      const tied = good.a & good.b;
      faulty.a = tied; faulty.b = tied; faulty.n1 = tied; faulty.n2 = tied;
      faulty.out = faulty.n1 ^ faulty.n2;
      activated = good.a !== good.b;
    } else if (fault === "transition-rise") {
      activated = previous.out === 0 && good.out === 1;
      faulty.out = activated ? 0 : good.out;
    }
    const propagated = good.out !== faulty.out;
    return {fault, good, faulty, previous, activated, propagated, observed: propagated, detected: propagated, result: propagated ? "detected" : "not-detected"};
  }
  function coverageSummary(states, mode) {
    const values = states || coverageExample;
    const count = key => { const value = Number(values[key] || 0); return Number.isFinite(value) ? Math.max(0, value) : 0; };
    const counts = {detected: count("detected"), "not-detected": count("not-detected"), untestable: count("untestable"), aborted: count("aborted")};
    const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
    const denominator = mode === "excluding-untestable" ? total - counts.untestable : total;
    const percentage = denominator ? +(counts.detected / denominator * 100).toFixed(1) : null;
    const all = mode !== "excluding-untestable";
    return {total, detected: counts.detected, denominator, percentage, mode: all ? "all" : "excluding-untestable", counts, formula: `${counts.detected} / ${denominator}`, applicable: denominator > 0};
  }

  // Small Boolean teaching circuit: h=a&b, p=a^b, out=h&p (therefore out is masked).
  // The available stimuli are all four input pairs. A control point forces h=1 on the
  // test path; an observe point captures h directly. Results are enumerated, not scored.
  const pointFaults = ["h-stuck-at-0", "p-stuck-at-0"];
  function pointCircuit(pattern, kind, fault, faulty) {
    const input = bits(pattern), baseH = input.a & input.b, baseP = input.a ^ input.b;
    let h = baseH, p = baseP;
    if (kind === "control" || kind === "both") h = 1;
    const faultBaseH = h, faultBaseP = p;
    if (faulty && fault === "h-stuck-at-0") h = 0;
    if (faulty && fault === "p-stuck-at-0") p = 0;
    const faultH = h, faultP = p;
    return {a: input.a, b: input.b, h, p, out: h & p, baseH, baseP, faultBaseH, faultBaseP, faultH, faultP};
  }
  function enumeratePoint(kind) {
    const selected = ["control", "observe", "both"].includes(kind) ? kind : "none";
    const detectedByFault = {};
    const activationByFault = {};
    pointFaults.forEach(fault => {
      detectedByFault[fault] = [];
      activationByFault[fault] = [];
      patterns.forEach(pattern => {
        const good = pointCircuit(pattern, selected, fault, false), faulty = pointCircuit(pattern, selected, fault, true);
        const activated = fault === "h-stuck-at-0" ? good.faultBaseH !== faulty.faultH : good.faultBaseP !== faulty.faultP;
        // The observe point taps the post-control h node. Compare the same node
        // on both good and faulty circuits; do not mix pre-control baseH with it.
        const observed = good.out !== faulty.out || ((selected === "observe" || selected === "both") && good.h !== faulty.h);
        if (activated) activationByFault[fault].push(pattern);
        if (observed) detectedByFault[fault].push(pattern);
      });
    });
    const detectedFaults = pointFaults.filter(fault => detectedByFault[fault].length > 0);
    const activationSet = pointFaults.filter(fault => activationByFault[fault].length > 0).map(fault => `${fault}: ${activationByFault[fault].join(",")}`).join("；") || "无";
    return {kind: selected, availableStimuli: patterns.slice(), faults: pointFaults.slice(), activationByFault, detectedByFault, detectedFaults, detectedCount: detectedFaults.length, activationSet, patternCount: patterns.length, teachingModel: true};
  }
  function testPointImpact(kind) { return enumeratePoint(kind); }

  const models = globalThis.DFTLabModels = globalThis.DFTLabModels || {};
  models.faults = {bits, circuit, simulate: simulateFault, coverageSummary, enumeratePoint, testPointImpact};
  if (typeof document === "undefined") return;
  const text = (root, selector, value) => { const node = root.querySelector(selector); if (node) node.textContent = String(value); };
  const enable = root => root.querySelectorAll("button, select").forEach(node => { node.disabled = false; });

  const atpg = document.querySelector("#fault-atpg-lab");
  if (atpg) {
    const run = () => {
      const data = simulateFault({fault: atpg.querySelector("[data-fault-setting]").value, pattern: atpg.querySelector("[data-pattern-setting]").value, previous: atpg.querySelector("[data-previous-setting]").value});
      text(atpg, '[data-field="inputs"]', `${data.good.a}${data.good.b} / ${data.previous.a}${data.previous.b}`); text(atpg, '[data-field="activated"]', data.activated ? "是" : "否"); text(atpg, '[data-field="propagated"]', data.propagated ? "是" : "否"); text(atpg, '[data-field="result"]', data.result === "detected" ? "检测到" : "未检测到"); text(atpg, '[data-field="out"]', `${data.good.out} → ${data.faulty.out}`); text(atpg, '[data-field="fault-badge"]', `${data.fault} · ${data.result}`); text(atpg, '[data-field="explanation"]', data.detected ? "故障被激活，差异沿当前路径传播到 out，因此本次模式可以观察到它。" : data.activated ? "故障位置被激活，但当前路径没有形成可观察输出差异；需要换刺激或增加观察结构。" : "当前输入没有激活所选故障；ATPG 需要搜索另一组刺激。"); atpg.dataset.result = data.result;
    };
    const reset = () => { atpg.querySelector('[data-fault-setting]').value = "stuck-at-0"; atpg.querySelector('[data-pattern-setting]').value = "10"; atpg.querySelector('[data-previous-setting]').value = "00"; text(atpg, '[data-field="inputs"]', "— / —"); text(atpg, '[data-field="activated"]', "尚未运行"); text(atpg, '[data-field="propagated"]', "尚未运行"); text(atpg, '[data-field="result"]', "尚未运行"); text(atpg, '[data-field="out"]', "—"); text(atpg, '[data-field="fault-badge"]', "当前无注入"); text(atpg, '[data-field="explanation"]', "先选择一个故障、当前模式和前一模式。transition 故障是否激活取决于前一捕获值到当前捕获值的变化。"); atpg.removeAttribute("data-result"); };
    enable(atpg); atpg.querySelector('[data-action="run"]').addEventListener("click", run); atpg.querySelector('[data-action="reset"]').addEventListener("click", reset); atpg.querySelector('[data-fault-setting]').addEventListener("change", run); atpg.querySelector('[data-pattern-setting]').addEventListener("change", run); atpg.querySelector('[data-previous-setting]').addEventListener("change", run); reset();
  }

  const coverage = document.querySelector("#coverage-lab");
  if (coverage) {
    const render = () => { const mode = coverage.querySelector("[data-coverage-setting]").value, data = coverageSummary(coverageExample, mode); Object.entries(data.counts).forEach(([key, value]) => { text(coverage, `[data-count="${key}"]`, value); const bar = coverage.querySelector(`[data-bar="${key}"]`); if (bar) bar.style.height = `${data.total ? Math.max(8, value / data.total * 100) : 8}%`; }); text(coverage, '[data-field="formula"]', `${mode === "all" ? "全目标检测比例" : "排除已证明不可测后的检测比例"} = ${data.formula}`); text(coverage, '[data-field="percentage"]', data.applicable ? `${data.percentage}%` : "不适用"); text(coverage, '[data-field="denominator"]', mode === "all" ? "分母保留 detected / not-detected / untestable / aborted" : "仅排除已证明不可测；aborted 仍在分母"); text(coverage, '[data-field="total"]', data.total); text(coverage, '[data-field="detected"]', data.detected); text(coverage, '[data-field="denom-count"]', data.denominator); text(coverage, '[data-field="coverage-result"]', data.applicable ? `${data.percentage}%` : "不适用"); text(coverage, '[data-field="explanation"]', mode === "all" ? "全目标检测比例把所有状态留在分母，展示整个目标列表中已有检测证据的比例。" : "此口径只排除已证明不可测；aborted 是未解决状态，仍留在分母，不能冒充正常的可测试故障覆盖率。"); };
    enable(coverage); coverage.querySelector('[data-action="coverage-run"]').addEventListener("click", render); coverage.querySelector('[data-action="coverage-reset"]').addEventListener("click", () => { coverage.querySelector('[data-coverage-setting]').value = "all"; render(); }); coverage.querySelector('[data-coverage-setting]').addEventListener("change", render); render();
  }

  const points = document.querySelector("#testpoints-lab");
  if (points) {
    const render = () => { const data = enumeratePoint(points.querySelector("[data-point-setting]").value); const activation = data.activationSet; const detected = data.detectedFaults.length ? data.detectedFaults.map(fault => `${fault} [${data.detectedByFault[fault].join(",")}]`).join("；") : "无"; text(points, '[data-field="activation-set"]', activation); text(points, '[data-field="detected-set"]', detected); text(points, '[data-field="detected-count"]', `${data.detectedCount} / ${data.faults.length}`); text(points, '[data-field="pattern-count"]', data.patternCount); text(points, '[data-field="explanation"]', `${data.kind === "none" ? "没有测试点：out=h&p 始终被掩蔽。" : data.kind === "control" ? "控制点把 h 强制为 1，使 p-stuck-at-0 的差异到达 out。" : data.kind === "observe" ? "观察点直接捕获 h，使 h-stuck-at-0 的差异绕过 out 的掩蔽。" : "控制点激励 p 故障，观察点捕获 h 故障；两条路径各自改变检测集合。"} 结果来自 ${data.patternCount} 个模式逐一比较，不是可控性分数或覆盖率预测。`); points.dataset.point = data.kind; };
    enable(points); points.querySelector('[data-action="point-evaluate"]').addEventListener("click", render); points.querySelector('[data-action="point-reset"]').addEventListener("click", () => { points.querySelector('[data-point-setting]').value = "none"; render(); }); points.querySelector('[data-point-setting]').addEventListener("change", render); render();
  }
})();
