"use strict";
(() => {
  const button = document.querySelector('#motion-toggle');
  const home = document.querySelector('.studio-home');
  if (!button || !home) return;
  const preference = matchMedia('(prefers-reduced-motion: reduce)');
  home.classList.add('motion-ready');
  let paused = preference.matches;
  const render = () => {
    home.classList.toggle('motion-paused', paused || document.hidden);
    button.disabled = preference.matches;
    button.textContent = preference.matches ? '已减少动态效果' : paused ? '播放动效' : '暂停动效';
    button.setAttribute('aria-pressed', String(paused));
  };
  button.addEventListener('click', () => { paused = !paused; render(); });
  preference.addEventListener('change', () => { paused = preference.matches; render(); });
  document.addEventListener('visibilitychange', render);
  window.addEventListener('pagehide', () => home.classList.add('motion-paused'));
  window.addEventListener('pageshow', render);
  render();
})();
