"use strict";
(() => {
  const global = globalThis;
  const models = global.DFTLabModels || (global.DFTLabModels = {});

  const MATRIX = [[0, 0, 0, 0], [0, 1, 1, 0], [1, 0, 1, 1], [1, 1, 0, 1]];

  function validText(value, pattern, name) {
    const text = String(value == null ? "" : value).toUpperCase();
    return new RegExp(pattern).test(text) ? { value: text } : { error: `${name} 格式错误：只能使用 ${pattern === "^[01?]{4}$" ? "4 位 0/1/?" : pattern === "^[01X]{4}$" ? "4 位 0/1/X" : "4 位 0/1"}` };
  }

  function matchesCare(candidate, care) {
    return care.every((bit, index) => bit === "?" || Number(bit) === candidate[index]);
  }

  function ternaryXor(values) {
    const known = values.filter(value => value !== "M");
    if (!known.length) return "M";
    if (known.some(value => value === "X")) return "X";
    return String(known.reduce((sum, value) => sum ^ Number(value), 0));
  }

  function compressionEvaluate(options) {
    const input = options || {};
    const care = validText(input.care == null ? "10?1" : input.care, "^[01?]{4}$", "care");
    const response = validText(input.response == null ? "1011" : input.response, "^[01X]{4}$", "响应");
    const mask = validText(input.mask == null ? "0010" : input.mask, "^[01]{4}$", "X mask");
    if (care.error || response.error || mask.error) return { valid: false, error: [care.error, response.error, mask.error].filter(Boolean).join("；") };
    const careBits = care.value.split("");
    const candidates = MATRIX.map((chainStimulus, index) => ({ inputs: [index >> 1, index & 1], chainStimulus }));
    const matches = candidates.filter(item => matchesCare(item.chainStimulus, careBits));
    const responseBits = response.value.split("");
    const maskBits = mask.value.split("");
    // mask=1 gates this chain's observed input to 0 and records lost observation as M.
    const observed = responseBits.map((bit, index) => maskBits[index] === "1" ? "M" : bit);
    const compacted = [ternaryXor([observed[0], observed[2]]), ternaryXor([observed[1], observed[3]])];
    const bypass = Boolean(input.bypass);
    const output = bypass ? observed.slice() : compacted;
    return {
      valid: true,
      care: care.value,
      response: response.value,
      mask: mask.value,
      candidates,
      matches,
      solvable: matches.length > 0,
      selectedInputs: matches.length ? matches[0].inputs : null,
      chainStimulus: matches.length ? matches[0].chainStimulus.map(String) : ["—", "—", "—", "—"],
      observed,
      compacted,
      output,
      bypass,
      xCount: observed.filter(bit => bit === "X").length,
      lostCount: observed.filter(bit => bit === "M").length,
      shiftCycles: 16,
      ratio: 2
    };
  }

  models.compression = { evaluate: compressionEvaluate, ternaryXor, matrix: MATRIX };

  function validBits(value, name) {
    const text = String(value == null ? "" : value);
    return /^[01]{4,32}$/.test(text) ? { value: text.split("").map(Number) } : { error: `${name} 必须是 4–32 位 0/1 字符` };
  }

  function hamming(oldBits, newBits) {
    return oldBits.reduce((sum, bit, index) => sum + (bit !== newBits[index] ? 1 : 0), 0);
  }

  function powerEvaluate(options) {
    const input = options || {};
    const shift = validBits(input.shift == null ? "10110011" : input.shift, "Shift 序列");
    const captureText = String(input.capture == null ? "110010100011" : input.capture);
    const capture = /^[01]{12}$/.test(captureText) ? {value: captureText.split("").map(Number)} : {error: "Capture 必须是 12 位 0/1（3 域各 4 位），不会自动截断或补齐"};
    const active = Array.isArray(input.activeDomains) ? input.activeDomains.slice(0, 3).map(Boolean) : [true, true, true];
    if (shift.error || capture.error) return { valid: false, error: [shift.error, capture.error].filter(Boolean).join("；") };
    // Each domain owns a fixed 4-bit teaching register. Shift flips are summed
    // across adjacent clock states; capture flips are Hamming(old,new).
    const oldRegs = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]];
    const newRegs = [0, 1, 2].map(domain => capture.value.slice(domain * 4, domain * 4 + 4));
    const captureByDomain = newRegs.map((bits, index) => active[index] ? hamming(oldRegs[index], bits) : 0);
    let shiftRegister = [0, 0, 0, 0];
    const shiftFlips = shift.value.reduce((sum, bit) => {
      const next = [bit, shiftRegister[0], shiftRegister[1], shiftRegister[2]];
      const flips = hamming(shiftRegister, next);
      shiftRegister = next;
      return sum + flips;
    }, 0);
    const captureFlips = captureByDomain.reduce((sum, value) => sum + value, 0);
    const schedule = input.schedule === "staggered" ? "staggered" : "parallel";
    const windowFlips = schedule === "parallel" ? captureByDomain : captureByDomain.map(value => value);
    const peak = schedule === "parallel" ? windowFlips.reduce((sum, value) => sum + value, 0) : Math.max.apply(null, windowFlips);
    const isolation = input.isolation !== false;
    const boundary = active.map((isOn, index) => isOn ? String(newRegs[index][3]) : (isolation ? "0" : "X"));
    return {
      valid: true, shift: shift.value, capture: capture.value, activeDomains: active,
      oldRegs, newRegs, captureByDomain, shiftFlips, captureFlips, schedule, isolation,
      peakConcurrentFlips: peak, boundary, window: schedule === "staggered" ? "D0 → D1 → D2" : "D0 ∥ D1 ∥ D2",
      shiftFinal: shiftRegister.slice()
    };
  }

  models.power = { evaluate: powerEvaluate, hamming };

  if (typeof document === "undefined") return;

  function setFields(root, prefix, values) {
    Object.keys(values).forEach(name => root.querySelectorAll(`[data-${prefix}-field="${name}"]`).forEach(node => { node.textContent = values[name]; }));
  }

  const compression = document.querySelector("#compression-lab");
  if (compression) {
    const input = name => compression.querySelector(`[data-compression-input="${name}"]`);
    const read = () => ({ care: input("care").value, response: input("response").value, mask: input("mask").value, bypass: input("bypass").checked });
    const render = () => {
      const result = compressionEvaluate(read());
      if (!result.valid) {
        setFields(compression, "compression", { explanation: result.error, output: "输入错误", matches: "—", stimulus: "—" });
        compression.dataset.result = "invalid";
        return;
      }
      const matchText = result.matches.map(item => `(${item.inputs.join(",")})`).join("、") || "无解";
      const output = result.output.join("");
      setFields(compression, "compression", {
        care: result.care, response: result.response, mask: result.mask, compact: result.compacted.join(""), bypass: result.bypass ? "开启" : "关闭",
        matches: matchText, stimulus: result.chainStimulus.join("") + " / " + result.observed.join(""), output,
        explanation: !result.solvable ? `care=${result.care} 在固定矩阵 [a,b,a⊕b,a] 中无可行输入；不能把它静默补成另一种刺激。` : result.bypass ? `找到 ${result.matches.length} 个输入候选；旁路显示完整未压缩响应 ${result.output.join("")}，M 表示该链观察被 mask 丢弃。` : `找到 ${result.matches.length} 个输入候选，选用 (a,b)=(${result.selectedInputs.join(",")}) 产生链刺激 ${result.chainStimulus.join("")}。未被 mask 的 X 继续传播；M 是已丢失观察，不是 0。`
      });
      result.chainStimulus.forEach((bit, index) => compression.querySelectorAll(`[data-compression-lane="${index}"]`).forEach(node => { node.textContent = bit; }));
      compression.dataset.result = !result.solvable ? "unsatisfiable" : result.output.indexOf("X") >= 0 ? "unknown" : "known";
    };
    const reset = () => { input("care").value = "10?1"; input("response").value = "1011"; input("mask").value = "0010"; input("bypass").checked = false; render(); };
    compression.querySelectorAll("input,select,button").forEach(node => { node.disabled = false; });
    compression.querySelector('[data-compression-action="apply"]').addEventListener("click", render);
    compression.querySelector('[data-compression-action="reset"]').addEventListener("click", reset);
    compression.querySelectorAll("input,select").forEach(node => node.addEventListener("change", render));
    render();
  }

  const power = document.querySelector("#test-power-lab");
  if (power) {
    const input = name => power.querySelector(`[data-power-input="${name}"]`);
    const domains = () => [0, 1, 2].map(index => power.querySelector(`[data-power-domain="${index}"]`).checked);
    const read = () => ({ shift: input("shift").value, capture: input("capture").value, schedule: input("schedule").value, isolation: input("isolation").checked, activeDomains: domains() });
    const render = () => {
      const result = powerEvaluate(read());
      if (!result.valid) { setFields(power, "power", { explanation: result.error, shiftFlips: "输入错误", captureFlips: "—", peak: "—" }); power.dataset.result = "invalid"; return; }
      setFields(power, "power", { shiftView: result.shift.join(""), captureView: result.capture.join(""), shiftFlips: String(result.shiftFlips), captureFlips: String(result.captureFlips), peak: String(result.peakConcurrentFlips), isolated: result.isolation ? "隔离开启" : "未隔离", boundary: result.boundary.join(" / "), window: result.window, explanation: `${result.schedule === "parallel" ? "并行" : "错峰"}调度按每域 old/new 寄存器 Hamming 计数：capture 翻转 ${result.captureFlips}，窗口峰值 ${result.peakConcurrentFlips}。跨域输出为 ${result.boundary.join("/")}；这不是 IR drop 或瓦特。` });
      result.captureByDomain.forEach((count, index) => power.querySelectorAll(`[data-power-domain-value="${index}"]`).forEach(node => { node.textContent = `${result.activeDomains[index] ? "ON" : "OFF"} · ${count} flip`; }));
      result.activeDomains.forEach((on, index) => power.querySelectorAll(`[data-power-domain-box="${index}"]`).forEach(node => { node.classList.toggle("is-off", !on); }));
      power.dataset.result = result.peakConcurrentFlips > 0 ? "active" : "managed";
    };
    const reset = () => { input("shift").value = "10110011"; input("capture").value = "110010100011"; input("schedule").value = "parallel"; input("isolation").checked = true; [0, 1, 2].forEach(index => { power.querySelector(`[data-power-domain="${index}"]`).checked = true; }); render(); };
    power.querySelectorAll("input,select,button").forEach(node => { node.disabled = false; });
    power.querySelector('[data-power-action="apply"]').addEventListener("click", render);
    power.querySelector('[data-power-action="reset"]').addEventListener("click", reset);
    power.querySelectorAll("input,select").forEach(node => node.addEventListener("change", render));
    render();
  }
})();
