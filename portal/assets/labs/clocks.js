"use strict";
/*
 * 三个 DFT 学习实验共用的纯计算模型。它们只计算教学输入，不代表某家
 * 工具的插入、STA、ATPG 或硅后签核结果。页面控制器在文件末尾，并且只
 * 绑定各自的实验根节点；因此这些模型也可以在 Node 中离线复核。
 */
(function (root) {
  var models = root.DFTLabModels = root.DFTLabModels || {};

  function number(value, fallback) {
    var result = Number(value);
    return Number.isFinite(result) ? result : fallback;
  }

  function readNumber(value, fallback, minimum, name, errors) {
    if (value === undefined || value === null || value === "") return fallback;
    var result = Number(value);
    if (!Number.isFinite(result)) {
      errors.push(name + " 必须是有限数字");
      return fallback;
    }
    if (result < minimum) {
      errors.push(name + " 不能小于 " + minimum);
      return minimum;
    }
    return result;
  }

  function atSpeedRun(options) {
    options = options || {};
    var errors = [];
    var modeValue = String(options.mode || "LOC").toUpperCase();
    var mode = modeValue === "LOS" ? "LOS" : "LOC";
    if (modeValue !== "LOC" && modeValue !== "LOS") errors.push("mode 必须为 LOC 或 LOS");
    var period = readNumber(options.periodNs, 10, 0.1, "periodNs", errors);
    var path = readNumber(options.pathDelayNs, 6.5, 0, "pathDelayNs", errors);
    var skew = readNumber(options.skewNs, 0.4, 0, "skewNs", errors);
    var setup = readNumber(options.setupNs, 0.5, 0, "setupNs", errors);
    var seLow = readNumber(options.seLowNs, 0.2, 0, "seLowNs", errors);
    var arrival = path + skew;
    var required = period - setup;
    var events = mode === "LOC" ? [
      { name: "shift", timeNs: -period, se: 1, description: "装入初始状态" },
      { name: "launch", timeNs: 0, se: 0, description: "功能时钟沿发起转换" },
      { name: "capture", timeNs: period, se: 0, description: "下一功能时钟沿采样" }
    ] : [
      { name: "shift-launch", timeNs: 0, se: 1, description: "最后一个移位沿同时发起转换" },
      { name: "se-low", timeNs: seLow, se: 0, description: "在捕获前关闭扫描选择" },
      { name: "capture", timeNs: period, se: 0, description: "功能时钟沿采样" }
    ];
    var seSetup = setup;
    var seSlack = period - seLow - seSetup;
    var seSafe = mode !== "LOS" || seSlack >= 0;
    var valid = errors.length === 0 && seSafe;
    if (!seSafe) errors.push("LOS 的 SE 必须在 capture 前关闭");
    var pass = valid && arrival <= required;
    return {
      valid: valid,
      errors: errors,
      mode: mode,
      periodNs: period,
      pathDelayNs: path,
      skewNs: skew,
      setupNs: setup,
      arrivalNs: Number(arrival.toFixed(3)),
      requiredNs: Number(required.toFixed(3)),
      slackNs: Number((required - arrival).toFixed(3)),
      seLowNs: Number(seLow.toFixed(3)),
      seSetupNs: Number(seSetup.toFixed(3)),
      seSlackNs: Number(seSlack.toFixed(3)),
      seSafe: seSafe,
      pass: pass,
      events: events,
      note: mode === "LOC" ? "LOC 在 SE=0 的功能沿发起转换；这里未模拟真实 OCC 波形。" : "LOS 利用最后一个扫描移位沿发起转换，SE 必须在捕获前安全关闭。"
    };
  }

  models.clocksAtSpeed = {
    run: atSpeedRun,
    simulate: atSpeedRun,
    modes: ["LOC", "LOS"]
  };

  function occRun(options) {
    options=options||{};
    var mode=String(options.mode||'shift').toLowerCase(), reset=Boolean(options.resetAsserted);
    var scanEnable=options.scanEnable!==false,testEnable=options.testEnable!==false,functionalClock=Boolean(options.functionalClock),resetBlocksClock=options.resetBlocksClock!==false;
    var errors=[];
    function count(value,fallback,name) {
      if(value===undefined)return fallback;
      var parsed=Number(value);
      if(value===null||value===''||!Number.isInteger(parsed)||parsed<0||parsed>16){errors.push(name+' 必须为 0～16 的整数');return 0;}
      return parsed;
    }
    var externalEdges=count(options.externalEdges,4,'externalEdges'),functionalEdges=count(options.functionalEdges,4,'functionalEdges');
    if(!['shift','capture'].includes(mode))errors.push('未知模式');
    var available=mode==='shift'?externalEdges:mode==='capture'&&functionalClock?functionalEdges:0;
    var reason='',allowed=false;
    if(errors.length)reason='输入无效：'+errors.join('；');
    else if(reset&&resetBlocksClock)reason='本教学配置在复位时关闭 OCC 输出；这不是所有 OCC 的通用复位策略。';
    else if(!testEnable)reason='测试使能关闭，拒绝测试请求；不代表功能模式时钟也被关闭。';
    else if(mode==='capture'&&scanEnable)reason='Capture 要求 SE=0，拒绝在扫描选择下发出捕获脉冲。';
    else if(mode==='shift'&&!scanEnable)reason='Shift 要求 SE=1，拒绝模式不一致的移位请求。';
    else if(!available)reason='没有所选时钟源的输入沿，输出计数保持为 0。';
    else {allowed=true;reason=mode==='shift'?'受控透传扫描输入沿。':'按教学请求最多放行一对 launch/capture，后续源沿被计数门控挡住。';}
    if(reset&&!resetBlocksClock)reason='本次显式配置复位不阻断时钟；不是通用规则。'+reason;
    var pulses=[],events=[],target=mode==='capture'?2:available;
    for(var index=0;index<available;index++) {
      var before=pulses.length,passed=allowed&&(mode==='shift'||before<2);
      var pulse=passed?(mode==='shift'?'shift':before===0?'launch':'capture'):null;
      if(passed)pulses.push(pulse);
      events.push({cycle:index+1,source:mode==='capture'?'功能时钟':'扫描时钟',sourceEdge:index+1,
        passed:passed,pulse:pulse,beforeEdges:before,outputEdges:pulses.length,remaining:Math.max(0,target-pulses.length),
        se:scanEnable?1:0,test:testEnable?1:0,reset:reset?1:0,
        reason:passed?(pulse==='shift'?'本源沿被透传，扫描状态可推进一次。':pulse==='launch'?'第一个允许沿用于 launch；仍等待 capture。':'第二个允许沿用于 capture；本请求的计数已满。'):allowed?'计数已满：当前源沿未到达扫描触发器。':reason});
    }
    return {valid:!errors.length,errors:errors,mode:mode,resetAsserted:reset,resetBlocksClock:resetBlocksClock,
      scanEnable:scanEnable,testEnable:testEnable,functionalClock:functionalClock,externalEdges:externalEdges,functionalEdges:functionalEdges,
      availableEdges:available,pulses:pulses,events:events,outputEdges:pulses.length,enabled:pulses.length>0,
      requestComplete:allowed&&pulses.length===target,reason:reason};
  }
  function occCreate(options) {
    var plan,cursor,frames;
    function copy(value){return JSON.parse(JSON.stringify(value));}
    function snapshot(){return copy(Object.assign({},frames[cursor],{done:cursor>=plan.events.length,plannedEdges:plan.outputEdges,totalSourceEdges:plan.availableEdges,valid:plan.valid,mode:plan.mode}));}
    function reset(settings){plan=occRun(settings);cursor=0;frames=[{cycle:0,source:'—',sourceEdge:null,passed:false,pulse:null,beforeEdges:0,outputEdges:0,
      remaining:plan.mode==='capture'?2:plan.availableEdges,se:plan.scanEnable?1:0,test:plan.testEnable?1:0,reset:plan.resetAsserted?1:0,
      reason:plan.availableEdges?'尚未送入源沿。'+plan.reason:plan.reason}];return snapshot();}
    reset(options);
    return {snapshot:snapshot,getHistory:function(){return copy(frames);},reset:reset,
      step:function(){if(cursor<plan.events.length){frames.push(copy(plan.events[cursor]));cursor++;}return snapshot();}};
  }
  models.clocksOcc={run:occRun,simulate:occRun,create:occCreate,modes:['shift','capture']};
  function scanBalance(lengths) {
    var errors = [];
    var raw = Array.isArray(lengths) ? lengths : [];
    var values = raw.map(function (value, index) {
      var parsed = Number(value);
      if (!Number.isFinite(parsed) || parsed < 1 || Math.floor(parsed) !== parsed) {
        errors.push("第 " + (index + 1) + " 条链必须是正整数");
        return 0;
      }
      return parsed;
    });
    var max = values.length ? Math.max.apply(Math, values) : 0;
    var min = values.length ? Math.min.apply(Math, values) : 0;
    var total = values.reduce(function (sum, value) { return sum + value; }, 0);
    return {
      lengths: values,
      valid: errors.length === 0 && values.length > 0,
      errors: errors,
      chainCount: values.length,
      totalFlops: total,
      max: max,
      min: min,
      spread: max - min,
      shiftCycles: max,
      balanced: errors.length === 0 && values.length > 0 && max - min <= 1
    };
  }

  function scanTiming(options) {
    options = options || {};
    var errors = [];
    var srcEdge = Number(options.sourceEdgeNs === undefined ? 0 : options.sourceEdgeNs);
    var dstEdge = Number(options.destinationEdgeNs === undefined ? 0.3 : options.destinationEdgeNs);
    var hold = Number(options.holdWindowNs === undefined ? 0.5 : options.holdWindowNs);
    var minDataDelay = Number(options.minDataDelayNs === undefined ? 0.2 : options.minDataDelayNs);
    var closedWindow = Number(options.closedWindowNs === undefined ? 5 : options.closedWindowNs);
    if (!Number.isFinite(srcEdge)) errors.push("sourceEdgeNs 必须是有限数字");
    if (!Number.isFinite(dstEdge)) errors.push("destinationEdgeNs 必须是有限数字");
    if (!Number.isFinite(hold) || hold < 0) errors.push("holdWindowNs 必须是非负有限数字");
    if (!Number.isFinite(minDataDelay) || minDataDelay < 0) errors.push("minDataDelayNs 必须是非负有限数字");
    if (!Number.isFinite(closedWindow) || closedWindow <= 0) errors.push("closedWindowNs 必须是正数");
    if (!Number.isFinite(srcEdge)) srcEdge = 0;
    if (!Number.isFinite(dstEdge)) dstEdge = 0.3;
    if (!Number.isFinite(hold) || hold < 0) hold = 0.5;
    if (!Number.isFinite(minDataDelay) || minDataDelay < 0) minDataDelay = 0.2;
    if (!Number.isFinite(closedWindow) || closedWindow <= 0) closedWindow = 5;
    var lockup = Boolean(options.lockup);
    var dataArrival = srcEdge + minDataDelay + (lockup ? closedWindow : 0);
    var requiredArrival = dstEdge + hold;
    var margin = dataArrival - requiredArrival;
    return {
      valid: errors.length === 0,
      errors: errors,
      sourceEdgeNs: srcEdge,
      destinationEdgeNs: dstEdge,
      holdWindowNs: hold,
      minDataDelayNs: minDataDelay,
      closedWindowNs: closedWindow,
      lockup: lockup,
      dataArrivalNs: Number(dataArrival.toFixed(3)),
      requiredArrivalNs: Number(requiredArrival.toFixed(3)),
      holdMarginNs: Number(margin.toFixed(3)),
      safe: errors.length === 0 && margin >= 0,
      note: lockup ? "示意 lock-up 窗口延迟新数据到达，改善保持裕量；没有移动目标时钟沿。" : "模型比较新数据到达与目标沿之后的保持窗口；真实跨沿关系仍需 STA/DFT DRC。"
    };
  }

  models.clocksScanEngineering = {
    balance: scanBalance,
    partition: scanBalance,
    timing: scanTiming,
    simulate: function (options) {
      options = options || {};
      return { balance: scanBalance(options.lengths || []), timing: scanTiming(options) };
    }
  };

  if (typeof document === "undefined") return;

  function text(rootNode, selector, value) {
    var node = rootNode.querySelector(selector);
    if (node) node.textContent = value;
  }
  function attr(rootNode, selector, name, value) {
    var node = rootNode.querySelector(selector);
    if (node) node.setAttribute(name, String(value));
  }
  function bind(rootNode, handlers) {
    var buttons = rootNode.querySelectorAll("button[data-action]");
    buttons.forEach(function (button) {
      button.disabled = false;
      button.addEventListener("click", function () { handlers[button.getAttribute("data-action")](); });
    });
    rootNode.querySelectorAll("select,input").forEach(function (control) {
      control.disabled = false;
      control.addEventListener("input", handlers.render);
      control.addEventListener("change", handlers.render);
    });
  }

  var speed = document.querySelector("#clocks-at-speed-lab");
  if (speed) {
    var resetSpeed = function () {
      speed.querySelector("[data-field=mode]").value = "LOC";
      speed.querySelector("[data-field=path]").value = "6.5";
      speed.querySelector("[data-field=period]").value = "10";
      speed.querySelector("[data-field=se-low]").value = "0.2";
      renderSpeed();
    };
    var renderSpeed = function () {
      var result = models.clocksAtSpeed.run({
        mode: speed.querySelector("[data-field=mode]").value,
        pathDelayNs: speed.querySelector("[data-field=path]").value,
        periodNs: speed.querySelector("[data-field=period]").value,
        seLowNs: speed.querySelector("[data-field=se-low]").value
      });
      text(speed, "[data-readout=arrival]", result.arrivalNs + " ns");
      text(speed, "[data-readout=slack]", result.slackNs + " ns");
      text(speed, "[data-readout=result]", result.pass ? "通过采样窗口" : "窗口不足");
      text(speed, "[data-readout=events]", result.events.map(function (event) { return event.name; }).join(" → "));
      var explanation = result.note + " 到达时间 " + result.arrivalNs + " ns，允许到达 " + result.requiredNs + " ns。" + (result.pass ? " 当前参数下有剩余裕量。" : " 当前参数下路径未及时稳定。");
      if (!result.seSafe) explanation += " SE 关闭时间晚于 capture，LOS 条件不合法。";
      if (!result.valid) explanation += " 输入校验：" + result.errors.join("；") + "。";
      text(speed, "[data-explanation]", explanation);
      var startX = result.mode === "LOS" ? 145 : 160;
      var captureX = 370;
      var arrivalX = startX + Math.min(1.35, Math.max(0, result.arrivalNs / Math.max(result.periodNs, 0.1))) * (captureX - startX);
      attr(speed, "[data-visual=launch]", "cx", startX);
      attr(speed, "[data-visual=arrival]", "cx", arrivalX);
      attr(speed, "[data-visual=arrival]", "cy", 120);
      attr(speed, "[data-visual=path]", "d", "M" + startX + " 120 C" + (startX + 65) + " 75, " + (arrivalX - 65) + " 75, " + arrivalX + " 120");
      speed.dataset.mode = result.mode;
      speed.dataset.result = result.pass ? "pass" : "fail";
    };
    bind(speed, { render: renderSpeed, reset: resetSpeed });
    renderSpeed();
  }

  var occ = document.querySelector('#clocks-occ-lab');
  if(occ) {
    var occModel,occTimer=null;
    var occPlay=occ.querySelector('[data-action=play]'),occStep=occ.querySelector('[data-action=step]'),occSpeed=occ.querySelector('[data-setting=speed]');
    function stopOcc(){if(occTimer!==null)clearInterval(occTimer);occTimer=null;occPlay.textContent='播放';}
    function renderOcc(frame) {
      var live=occModel.snapshot(),s=frame||live;
      occ.dataset.step=String(live.cycle);occ.dataset.viewStep=String(s.cycle);occ.dataset.mode=live.mode;occ.dataset.result=s.passed?'pass':'hold';
      text(occ,'[data-readout=edges]',s.outputEdges+' / '+live.plannedEdges);
      text(occ,'[data-readout=pulses]',s.pulse||'本沿未放行');text(occ,'[data-readout=result]',s.cycle?(s.passed?'本沿放行':'本沿阻断'):'尚无输出');
      text(occ,'[data-readout=remaining]',s.remaining);text(occ,'[data-readout=cycle]',s.cycle+' / '+live.totalSourceEdges);
      text(occ,'[data-explanation]',s.reason+' SE='+s.se+'，Test Enable='+s.test+'，Reset='+s.reset+'；计数 '+s.beforeEdges+' → '+s.outputEdges+'。条件变化会重新开始，动画速度不改变门控逻辑。');
      text(occ,'[data-occ-view]',frame?'回看第 '+s.cycle+' 个源沿；下一次操作从最新第 '+live.cycle+' 沿继续，不改写记录。':'当前状态；点击表中源沿可回看。');
      text(occ,'[data-occ-detail]','源时钟提供输入沿，OCC 不凭空产生沿。SE 选择测试模式；Test Enable 决定是否接受测试请求。当前计数 '+s.outputEdges+'，'+(live.mode==='capture'?'一对 launch/capture 计数达到 2 后阻断余下源沿。':'每个被允许的扫描沿使计数增加 1。')+'复位是否门控时钟取决于实现，本页采用复位阻断策略。');
      occ.querySelectorAll('[data-visual=pulse]').forEach(function(node,index){node.setAttribute('opacity',index<s.outputEdges?'1':'0.16');node.setAttribute('data-active',String(index<s.outputEdges));});
      occ.querySelectorAll('[data-occ-edge]').forEach(function(button){button.setAttribute('aria-pressed',String(Number(button.dataset.occEdge)===s.cycle));});
      occStep.disabled=live.done;occPlay.disabled=live.done;occ.querySelector('[data-action=latest]').disabled=!frame;
    }
    function recordOcc() {
      var body=occ.querySelector('[data-occ-history]');body.replaceChildren();
      occModel.getHistory().forEach(function(event){
        var tr=document.createElement('tr'),th=document.createElement('th'),button=document.createElement('button');th.scope='row';button.type='button';button.dataset.occEdge=String(event.cycle);button.textContent=event.cycle?'↑ '+event.cycle:'初始';button.setAttribute('aria-label','查看源沿 '+event.cycle);
        button.addEventListener('click',function(){stopOcc();renderOcc(event);});th.append(button);tr.append(th);
        [event.source,event.se,event.test,event.reset,event.passed?'放行':'未放行',event.pulse||'—',event.beforeEdges+' → '+event.outputEdges,event.remaining].forEach(function(value){var td=document.createElement('td');td.textContent=value;tr.append(td);});body.append(tr);
      });
    }
    function configureOcc() {
      stopOcc();occModel=models.clocksOcc.create({mode:occ.querySelector('[data-field=mode]').value,scanEnable:occ.querySelector('[data-field=se]').checked,testEnable:occ.querySelector('[data-field=test]').checked,
        resetAsserted:occ.querySelector('[data-field=reset]').checked,functionalClock:occ.querySelector('[data-field=functional]').checked,externalEdges:4,functionalEdges:4});recordOcc();renderOcc();
    }
    function stepOcc(){var s=occModel.step();recordOcc();renderOcc();if(s.done)stopOcc();}
    occ.querySelectorAll('button,input,select').forEach(function(node){node.disabled=false;});
    occStep.addEventListener('click',function(){stopOcc();stepOcc();});
    occPlay.addEventListener('click',function(){if(occTimer!==null){stopOcc();return;}renderOcc();occPlay.textContent='暂停';occTimer=setInterval(stepOcc,850/Number(occSpeed.value));});
    occSpeed.addEventListener('change',function(){if(occTimer!==null){clearInterval(occTimer);occTimer=setInterval(stepOcc,850/Number(occSpeed.value));}});
    occ.querySelector('[data-action=latest]').addEventListener('click',function(){stopOcc();renderOcc();});
    occ.querySelectorAll('[data-field]').forEach(function(control){control.addEventListener('change',configureOcc);});
    occ.querySelector('[data-action=reset]').addEventListener('click',function(){
      occ.querySelector('[data-field=mode]').value='shift';occ.querySelector('[data-field=se]').checked=true;occ.querySelector('[data-field=test]').checked=true;occ.querySelector('[data-field=functional]').checked=false;occ.querySelector('[data-field=reset]').checked=false;configureOcc();
    });
    document.addEventListener('visibilitychange',function(){if(document.hidden)stopOcc();});
    root.addEventListener('pagehide',stopOcc);configureOcc();
  }
  var scan = document.querySelector("#clocks-scan-engineering-lab");
  if (scan) {
    var resetScan = function () {
      scan.querySelector("[data-field=lengths]").value = "8,8,7,9";
      scan.querySelector("[data-field=edge]").value = "0.3";
      scan.querySelector("[data-field=lockup]").checked = false;
      renderScan();
    };
    var renderScan = function () {
      var lengths = scan.querySelector("[data-field=lengths]").value.split(",").map(function (item) { return item.trim(); });
      var balance = models.clocksScanEngineering.balance(lengths);
      var timing = models.clocksScanEngineering.timing({
        destinationEdgeNs: scan.querySelector("[data-field=edge]").value,
        lockup: scan.querySelector("[data-field=lockup]").checked
      });
      text(scan, "[data-readout=balance]", balance.lengths.join(" / "));
      text(scan, "[data-readout=spread]", balance.spread + " bit");
      text(scan, "[data-readout=cycles]", balance.shiftCycles + " 个移位沿");
      text(scan, "[data-readout=timing]", timing.safe ? "保持安全" : "可能违反保持");
      var explanation = (balance.balanced ? "链长接近平衡。" : "链长差异会让短链等待最长链完成。") + " " + timing.note;
      if (!balance.valid) explanation += " 链长校验：" + balance.errors.join("；") + "。";
      if (!timing.valid) explanation += " 时序校验：" + timing.errors.join("；") + "。";
      text(scan, "[data-explanation]", explanation);
      var maxLength = Math.max.apply(Math, balance.lengths.concat([1]));
      balance.lengths.forEach(function (length, index) {
        attr(scan, "[data-visual=bar-" + index + "]", "width", 48 + Math.round(250 * length / maxLength));
      });
      attr(scan, "[data-visual=lockup]", "opacity", scan.querySelector("[data-field=lockup]").checked ? "1" : "0.22");
      attr(scan, "[data-visual=edge]", "x1", 470 + Math.max(-1, Math.min(1, Number(scan.querySelector("[data-field=edge]").value) || 0)) * 80);
      attr(scan, "[data-visual=edge]", "x2", 470 + Math.max(-1, Math.min(1, Number(scan.querySelector("[data-field=edge]").value) || 0)) * 80);
      scan.dataset.result = timing.safe && balance.balanced && balance.valid && timing.valid ? "pass" : "review";
    };
    bind(scan, { render: renderScan, reset: resetScan });
    renderScan();
  }
})(typeof globalThis !== "undefined" ? globalThis : this);


