"use strict";
(() => {
  const filter = document.querySelector("#document-filter");
  if (filter) filter.addEventListener("input", () => {
    const query = filter.value.normalize("NFKC").toLocaleLowerCase();
    for (const item of document.querySelectorAll(".document-list a")) {
      item.hidden = !item.textContent.normalize("NFKC").toLocaleLowerCase().includes(query);
    }
  });
  const current = document.querySelector(".document-list a.active");
  if (current) current.scrollIntoView({block: "nearest"});
  if (document.body.dataset.internalEntry === "true") {
    const entry = new URL("../../yellow/.site/entry.js", location.href);
    const script = document.createElement("script");
    script.src = entry.href;
    script.onload = () => {
      if (window.DFT_INTERNAL_READY) location.replace(new URL("index.html", entry).href);
    };
    script.onerror = () => {
      const message = document.createElement('p'); message.setAttribute('role', 'status');
      message.textContent = '内部页面入口加载失败：可能尚未生成、交付包不完整，或浏览器阻止本地脚本。请核对 yellow/.site/entry.js，或直接打开 yellow/.site/index.html、使用本地服务。';
      document.querySelector('#main').prepend(message);
    };
    document.head.append(script);
  }
})();
