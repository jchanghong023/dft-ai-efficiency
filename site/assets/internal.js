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
    script.onerror = () => { /* Keep the readable empty state when local documents are absent. */ };
    document.head.append(script);
  }
})();
