"use strict";
(() => {
  const dialog = document.querySelector("#search-dialog");
  const input = document.querySelector("#search-input");
  const results = document.querySelector("#search-results");
  const status = document.querySelector("#search-status");
  const base = document.body.dataset.base;
  const normalize = value => value.normalize("NFKC").toLocaleLowerCase();
  // Map normalized matches back to source offsets (full-width text, emoji, ligatures).
  const ranges = (text, terms) => {
    let folded = '', offsets = [], position = 0;
    for (const char of text) {
      const value = normalize(char);
      for (let i = 0; i < value.length; i++) offsets.push([position, position + char.length]);
      folded += value; position += char.length;
    }
    const matches = [];
    for (const term of terms) {
      if (!term) continue;
      let start = 0;
      while ((start = folded.indexOf(term, start)) !== -1) {
        matches.push([offsets[start][0], offsets[start + term.length - 1][1]]); start += term.length;
      }
    }
    matches.sort((a,b) => a[0]-b[0]);
    const merged = [];
    for (const match of matches) {
      const last = merged.at(-1);
      if (last && match[0] <= last[1]) last[1] = Math.max(last[1],match[1]); else merged.push([...match]);
    }
    return merged;
  };
  const highlight = (text, terms) => {
    const fragment = document.createDocumentFragment(); let end = 0;
    for (const [start,stop] of ranges(text,terms)) {
      fragment.append(document.createTextNode(text.slice(end,start)));
      const mark = document.createElement('mark'); mark.className = 'search-hit'; mark.textContent = text.slice(start,stop);
      fragment.append(mark); end=stop;
    }
    fragment.append(document.createTextNode(text.slice(end))); return fragment;
  };
  window.DFTSearch = {normalize,ranges,highlight};
  const currentArea = document.body.dataset.area;
  const scope = currentArea === 'home' ? '全部公共内容（含 DFT，不含内部文档）' : document.querySelector('#search-title').textContent.replace(/^搜索/, '');
  const idleStatus = `当前范围：${scope} · 本地全文搜索`;
  status.textContent = idleStatus;
  const everydayCommands = new Set(['pages/command-model.html', 'pages/command-resume.html', 'pages/command-compact.html']);
  const documents = (window.DFT_SEARCH || [])
    .filter(item => currentArea === 'home' ? ['start', 'team', 'maintenance', 'dft'].includes(item.area) : item.area === currentArea)
    .map(item => ({...item, normalized: normalize(item.title + " " + item.text),
      purpose: normalize((item.sections || []).find(s => s.title === '功能与场景')?.text.split(/[。！？]/)[0] || '')}));
  const openSearch = () => { dialog.showModal(); input.focus(); };
  document.querySelector(".search-trigger").addEventListener("click", openSearch);
  document.querySelectorAll('.module-search').forEach(button => button.addEventListener('click', openSearch));
  document.querySelector("#search-close").addEventListener("click", () => dialog.close());
  document.addEventListener("keydown", event => {
    if (event.key === "/" && !dialog.open && !["INPUT", "TEXTAREA"].includes(document.activeElement.tagName) && !document.activeElement.isContentEditable) {
      event.preventDefault(); openSearch();
    }
  });
  const more = document.createElement('button'); more.type='button'; more.className='search-more'; more.hidden=true; results.after(more);
  let hits=[], shown=0, terms=[], query='';
  const appendResults = () => {
    const next=hits.slice(shown,shown+40);
    for (const item of next) {
      const sections=item.sections || [];
      const section=sections.find(s => terms.every(term => normalize(s.title+' '+s.text).includes(term)))
        || sections.find(s => terms.some(term => normalize(s.text).includes(term)));
      const link=document.createElement('a'); link.className='search-result';
      link.href=base+item.url+'?q='+encodeURIComponent(input.value.trim())+(section ? '#'+encodeURIComponent(section.id) : '');
      const title=document.createElement('strong'); title.append(highlight(item.title,terms));
      const location=document.createElement('small'); location.className='search-location'; location.textContent=item.location+(section ? ' / '+section.title : '');
      const text=section ? section.text : item.text, matches=ranges(text,terms);
      const offset=Math.max(0,(matches[0]?.[0] || 0)-35);
      const excerpt=document.createElement('small'); excerpt.append(highlight((offset ? '…' : '')+text.slice(offset,offset+155)+(offset+155<text.length ? '…' : ''),terms));
      link.append(title,location,excerpt); results.append(link);
    }
    shown+=next.length;
    status.textContent=`当前范围：${scope} · ` + (hits.length ? `找到 ${hits.length} 篇文档，已显示 ${shown} 篇` : '没有找到结果，请换关键词或进入其他分区。');
    more.hidden=shown>=hits.length; more.textContent=`继续显示（剩余 ${hits.length-shown} 篇）`;
  };
  more.addEventListener('click',appendResults);
  input.addEventListener('input',() => {
    query=normalize(input.value.trim()); results.replaceChildren(); more.hidden=true; shown=0; hits=[];
    if(!query){ status.textContent=idleStatus; return; }
    terms=query.split(/\s+/);
    const relevance = item => {
      const title = normalize(item.title);
      let score = title === query ? 120 : title.includes(query) ? 70 : 0;
      if (terms.every(term => item.purpose.includes(term))) {
        score += 35 + 15 / Math.max(1, item.purpose.length);
        if (everydayCommands.has(item.url)) score += 10;
      }
      return score;
    };
    hits=documents.filter(item=>terms.every(term=>item.normalized.includes(term)))
      .sort((a,b)=>relevance(b)-relevance(a));
    appendResults();
  });
  let toastTimer;
  const notify = message => { const toast = document.querySelector("#toast"); toast.textContent = message; toast.style.display = "block"; clearTimeout(toastTimer); toastTimer = setTimeout(() => { toast.style.display = "none"; }, 2200); };
  const copyText = async (text, button, message) => {
    try {
      if (!navigator.clipboard) throw new Error("fallback");
      await navigator.clipboard.writeText(text); notify(message);
    } catch (_) {
      const area = document.createElement("textarea"); area.value = text; area.style.position = "fixed"; area.style.opacity = "0"; document.body.append(area); area.select();
      let copied = false;
      try { copied = document.execCommand("copy"); } catch (_) { /* Selection remains available in the page. */ }
      area.remove(); button.focus(); notify(copied ? message : "复制不可用，请选择代码手动复制");
    }
  };
  for (const button of document.querySelectorAll('[data-copy]')) {
    button.hidden = false;
    button.addEventListener('click', () => copyText(button.dataset.copy, button, '已复制命令；粘贴到 OMP 输入框使用'));
  }
  for (const pre of document.querySelectorAll("pre")) {
    const code = pre.querySelector("code"); if (!code) continue;
    const button = document.createElement("button"); button.type = "button"; button.className = "copy-button"; button.textContent = "复制"; button.setAttribute("aria-label", "复制代码");
    button.addEventListener("click", () => copyText(code.textContent, button, "已复制代码")); pre.append(button);
  }
})();
