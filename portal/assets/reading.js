"use strict";
(() => {
  const filter = document.querySelector('#nav-filter');
  if (filter) filter.addEventListener('input', () => {
    const query = filter.value.normalize('NFKC').toLowerCase();
    document.querySelectorAll('.module-navigation a').forEach(link => { link.hidden = !link.textContent.normalize('NFKC').toLowerCase().includes(query); });
    document.querySelectorAll('.nav-group').forEach(group => { group.hidden = !Array.from(group.querySelectorAll('a')).some(link => !link.hidden); });
  });
  const current = document.querySelector('.module-navigation a.active');
  if (current) {
    const nav = current.closest('.module-navigation');
    nav.scrollTop = Math.max(0, current.getBoundingClientRect().top - nav.getBoundingClientRect().top - nav.clientHeight / 2);
  }
  const links = Array.from(document.querySelectorAll('aside.toc a[href^="#"]')).filter(link => link.getAttribute('href') !== '#main');
  const headings = links.map(link => ({link, target:document.getElementById(decodeURIComponent(link.getAttribute('href').slice(1)))})).filter(item => item.target);
  let pending = false;
  const followHeading = () => {
    const active = headings.filter(item => item.target.getBoundingClientRect().top <= 145).at(-1) || headings[0];
    headings.forEach(item => {
      item.link.classList.toggle('current', item === active);
      if (item === active) item.link.setAttribute('aria-current', 'location'); else item.link.removeAttribute('aria-current');
    });
    pending = false;
  };
  addEventListener('scroll', () => { if (!pending) { pending = true; requestAnimationFrame(followHeading); } }, {passive:true});
  followHeading();

  // Lightweight lexical colour for declared languages only. Plain text diagrams stay untouched.
  const keywords = new Set('if else elif then fi for while do done in return def class import from as with try except finally raise pass True False None function const let var new throw async await export module endmodule input output wire reg logic always always_ff assign begin end posedge negedge case endcase parameter localparam integer initial task endtask'.split(' '));
  for (const pre of document.querySelectorAll('.article pre')) {
    const code = pre.querySelector('code'); if (!code) continue;
    const language = Array.from(code.classList).find(name => name.startsWith('language-'))?.slice(9) || 'text';
    const label = document.createElement('span'); label.className = 'code-language'; label.textContent = language; pre.append(label);
    if (!['python','py','bash','sh','shell','javascript','js','typescript','ts','verilog','systemverilog','json'].includes(language)) continue;
    const hashComments = ['python','py','bash','sh','shell'].includes(language);
    const pattern = hashComments ? /("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|#[^\n]*|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b)/g : /("(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\/\/[^\n]*|\/\*[\s\S]*?\*\/|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*\b)/g;
    const source = code.textContent; const fragment = document.createDocumentFragment(); let end = 0;
    for (const match of source.matchAll(pattern)) {
      fragment.append(document.createTextNode(source.slice(end, match.index)));
      const value = match[0]; const span = document.createElement('span'); span.textContent = value;
      span.className = /^['"]/.test(value) ? 'syntax-string' : /^(#|\/\/|\/\*)/.test(value) ? 'syntax-comment' : /^\d/.test(value) ? 'syntax-number' : keywords.has(value) ? 'syntax-keyword' : '';
      fragment.append(span); end = match.index + value.length;
    }
    fragment.append(document.createTextNode(source.slice(end))); code.replaceChildren(fragment);
  }
  // A search result carries only a local query and heading anchor, never a request.
  const searchQuery = new URL(location.href).searchParams.get('q');
  if (searchQuery && window.DFTSearch) {
    const article=document.querySelector('main.article');
    const terms=window.DFTSearch.normalize(searchQuery.trim()).split(/\s+/).filter(Boolean);
    if(article && terms.length) {
      const walker=document.createTreeWalker(article,4), groups=new Map();
      while(walker.nextNode()) {
        const node=walker.currentNode;
        if(!node.parentElement || node.parentElement.closest('script,style,button,select,textarea,svg,mark,.dft-lab,.dft-demo,.breadcrumb,.article-end'))continue;
        const block=node.parentElement.closest('pre,p,li,td,th,h1,h2,h3,h4,h5,h6,blockquote') || node.parentElement;
        if(!groups.has(block))groups.set(block,[]);groups.get(block).push(node);
      }
      // Match across inline emphasis and syntax spans, but never across unrelated blocks.
      const occurrences=[];
      for(const nodes of groups.values()){
        const text=nodes.map(node=>node.textContent).join(''), ranges=window.DFTSearch.ranges(text,terms);
        const matched=ranges.map(()=>[]);let offset=0;
        for(const node of nodes){
          const value=node.textContent,fragment=document.createDocumentFragment();let end=0;
          ranges.forEach(([start,stop],index)=>{
            const a=Math.max(0,start-offset),b=Math.min(value.length,stop-offset);if(a>=b)return;
            fragment.append(document.createTextNode(value.slice(end,a)));
            const mark=document.createElement('mark');mark.className='search-hit';mark.textContent=value.slice(a,b);
            fragment.append(mark);matched[index].push(mark);end=b;
          });
          if(end){fragment.append(document.createTextNode(value.slice(end)));node.replaceWith(fragment);}
          offset+=value.length;
        }
        occurrences.push(...matched.filter(parts=>parts.length));
      }
      const marks=occurrences.flat();
      const bar=document.createElement('div'); bar.className='search-context';
      const info=document.createElement('span');
      info.textContent=`搜索“${searchQuery}” · 正文 ${occurrences.length} 处匹配`; bar.append(info);
      let selected=-1;
      const move=delta=>{
        if(!occurrences.length)return;
        selected=selected<0 ? (delta>0 ? 0 : occurrences.length-1) : (selected+delta+occurrences.length)%occurrences.length;
        occurrences.forEach((parts,i)=>parts.forEach(mark=>mark.classList.toggle('active-hit',i===selected)));
        occurrences[selected][0].scrollIntoView({block:'center'}); info.textContent=`搜索“${searchQuery}” · ${selected+1} / ${occurrences.length}`;
      };
      [['上一处',-1],['下一处',1]].forEach(([text,delta])=>{
        const button=document.createElement('button');button.type='button';button.textContent=text;button.disabled=!marks.length;button.addEventListener('click',()=>move(delta));bar.append(button);
      });
      const clear=document.createElement('button');clear.type='button';clear.textContent='清除高亮';
      clear.addEventListener('click',()=>{marks.forEach(mark=>mark.replaceWith(document.createTextNode(mark.textContent)));bar.remove();});bar.append(clear);
      const breadcrumb=article.querySelector('.breadcrumb'); if(breadcrumb)breadcrumb.after(bar);else article.prepend(bar);
      const anchor=new URL(location.href).hash;
      if(anchor){const target=document.getElementById(decodeURIComponent(anchor.slice(1)));if(target)requestAnimationFrame(()=>target.scrollIntoView({block:'start'}));}
    }
  }

  let viewer;
  document.querySelectorAll('.article img').forEach(img => {
    img.classList.add('zoomable'); img.tabIndex = 0; img.setAttribute('role','button'); img.setAttribute('aria-label', '放大图片：' + (img.alt || '文档图片'));
    const open = () => {
      if (!viewer) {
        viewer = document.createElement('dialog'); viewer.className = 'image-dialog'; viewer.setAttribute('aria-label','放大图片');
        const close = document.createElement('button'); close.type = 'button'; close.textContent = '关闭 · Esc'; close.addEventListener('click', () => viewer.close());
        viewer.append(close, document.createElement('img'), document.createElement('p')); document.body.append(viewer);
      }
      viewer.querySelector('img').src = img.src; viewer.querySelector('img').alt = img.alt; viewer.querySelector('p').textContent = img.alt; viewer.showModal();
    };
    img.addEventListener('click', open); img.addEventListener('keydown', e => { if (['Enter',' '].includes(e.key)) { e.preventDefault(); open(); } });
  });
  // View controls never advance or alter the circuit model.
  document.querySelectorAll('.dft-lab svg[viewBox], .dft-demo svg[viewBox]').forEach(svg => {
    svg.setAttribute('role','group');
    const viewport = document.createElement('div'); viewport.className = 'drawing-viewport';
    svg.before(viewport); viewport.append(svg);
    const toolbar = document.createElement('div'); toolbar.className = 'drawing-toolbar';
    const label = document.createElement('span'); label.textContent = '画布 100%'; toolbar.append(label);
    let zoom = 1;
    const apply = () => { svg.style.width = `${zoom * 100}%`; label.textContent = `画布 ${Math.round(zoom * 100)}%`; };
    [['−',-.25],['＋',.25],['适应',0]].forEach(([title,delta]) => {
      const button = document.createElement('button'); button.type='button'; button.textContent=title; button.setAttribute('aria-label', title === '−' ? '缩小电路' : title === '＋' ? '放大电路' : '适应画布');
      button.addEventListener('click', () => { zoom = delta === 0 ? 1 : Math.min(2.5,Math.max(1,zoom + delta)); apply(); }); toolbar.append(button);
    });
    viewport.before(toolbar);
    viewport.tabIndex = 0; viewport.setAttribute('aria-label','电路画布，放大后可用方向键或滚动条查看局部');
    const detail = document.createElement('p'); detail.className = 'signal-detail'; detail.textContent = '选择图中的文字或数值查看当前读数；放大后可滚动查看局部。'; viewport.after(detail);
    let selected = null;
    const signalHelp = {
      si:'SI · 当前扫描输入', so:'SO · 当前扫描输出', se:'SE · 1 选择扫描路径，0 选择功能路径',
      lfsr:'LFSR · 本拍使用的伪随机激励', response:'DUT · 本拍逻辑响应',
      misr:'MISR · 累积响应签名', signature:'签名 · 当前累积结果', expected:'期望 · 同一模型的无故障结果'
    };
    const show = () => {
      if(!selected) return;
      const q = selected.getAttribute('data-q');
      const field = selected.getAttribute('data-field');
      const description = q !== null ? `Q${Number(q)+1} · 扫描寄存器状态` : signalHelp[field] || '图中标签 / 当前读数';
      detail.textContent = `${description}：${selected.textContent.trim()}。单步和播放使用同一份模型状态，缩放不改变电路结果。`;
    };
    svg.querySelectorAll('text').forEach(text => {
      text.setAttribute('tabindex','0'); text.setAttribute('role','button');
      text.addEventListener('click', () => {selected=text; show();});
      text.addEventListener('keydown', e => {if(['Enter',' '].includes(e.key)){e.preventDefault();selected=text;show();}});
    });
    const observer = new MutationObserver(show); observer.observe(svg,{subtree:true,characterData:true,childList:true});
    window.addEventListener('pagehide', () => observer.disconnect());
    window.addEventListener('pageshow', () => observer.observe(svg,{subtree:true,characterData:true,childList:true})); apply();
  });
})();
