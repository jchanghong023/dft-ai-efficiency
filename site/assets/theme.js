"use strict";
(() => {
  const root = document.documentElement;
  const key = "dft-theme";
  let preference = "auto";
  let timer;
  const readPreference = () => {
    try {
      const saved = localStorage.getItem(key);
      return saved === "light" || saved === "dark" ? saved : "auto";
    } catch (_) { return preference; }
  };
  const render = () => {
    const now = new Date();
    const daytime = now.getHours() >= 7 && now.getHours() < 19;
    const theme = preference === "auto" ? (daytime ? "light" : "dark") : preference;
    root.dataset.theme = theme;
    root.style.colorScheme = theme;
    const toggle = document.querySelector("#theme-toggle");
    if (toggle) {
      const next = theme === "dark" ? "浅色" : "深色";
      const current = theme === "dark" ? "深色" : "浅色";
      toggle.setAttribute("aria-label", "切换到" + next + "模式");
      toggle.title = "当前：" + current + "模式" + (preference === "auto" ? "（自动）" : "（手动）") + "；点击切换";
      document.querySelector("#theme-label").textContent = next;
      document.querySelector("#theme-auto").setAttribute("aria-pressed", String(preference === "auto"));
    }
    clearTimeout(timer);
    if (preference === "auto") {
      const nextBoundary = new Date(now);
      if (now.getHours() < 7) nextBoundary.setHours(7, 0, 0, 0);
      else if (now.getHours() < 19) nextBoundary.setHours(19, 0, 0, 0);
      else { nextBoundary.setDate(nextBoundary.getDate() + 1); nextBoundary.setHours(7, 0, 0, 0); }
      timer = setTimeout(render, nextBoundary.getTime() - now.getTime() + 50);
    }
  };
  const choose = value => {
    preference = value;
    try {
      if (value === "auto") localStorage.removeItem(key);
      else localStorage.setItem(key, value);
    } catch (_) { /* Storage may be unavailable for a local file; switching still works. */ }
    render();
  };
  const refresh = () => { preference = readPreference(); render(); };
  refresh(); // Resolve before styles paint, including file:// navigation.
  const bind = () => {
    const controls = document.querySelector(".theme-controls");
    if (!controls) return;
    controls.hidden = false;
    document.querySelector("#theme-toggle").addEventListener("click", () => choose(root.dataset.theme === "dark" ? "light" : "dark"));
    document.querySelector("#theme-auto").addEventListener("click", () => choose("auto"));
    render();
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", bind, {once:true});
  else bind();
  document.addEventListener("visibilitychange", () => { if (!document.hidden) refresh(); });
  window.addEventListener("pageshow", refresh);
  window.addEventListener("pagehide", () => clearTimeout(timer));
  window.addEventListener("storage", event => { if (event.key === key || event.key === null) refresh(); });
})();
