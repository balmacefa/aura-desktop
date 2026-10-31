(function () {
  'use strict';
  var REPO = 'balmacefa/aura-desktop';
  var SCENES = [
    { id: 'estela', en: 'Trail', es: 'Estela', den: 'Your cursor leaves a living trail of light; clicks burst into sparks.', des: 'Tu cursor deja una estela de luz; los clics lanzan chispas.' },
    { id: 'constelacion', en: 'Constellation', es: 'Constelación', den: 'Stars connect and drift toward your mouse.', des: 'Las estrellas se conectan y siguen a tu ratón.' },
    { id: 'orbes', en: 'Orbs', es: 'Orbes', den: 'Soft glowing orbs that respond to your movement.', des: 'Orbes luminosos que responden a tu movimiento.' },
    { id: 'aurora', en: 'Aurora', es: 'Aurora boreal', den: 'Northern lights that ripple as you move.', des: 'Una aurora boreal que ondula cuando te mueves.' },
    { id: 'malla', en: 'Wave mesh', es: 'Malla de olas', den: 'A mesh of waves rippling from your cursor.', des: 'Una malla de olas que se propagan desde tu cursor.' }
  ];
  var lang = 'en', cur = 0, active = false;
  var $ = function (s) { return document.querySelector(s); };
  var frame = $('#frame'), play = $('#play'), tabs = $('#tabs'), desc = $('#scene-desc');

  function detect() {
    try { var s = localStorage.getItem('aura-lang'); if (s === 'en' || s === 'es') return s; } catch (e) {}
    var l = (navigator.languages && navigator.languages[0]) || navigator.language || 'en';
    return /^es/i.test(l) ? 'es' : 'en';
  }
  function applyLang(l) {
    lang = l; document.documentElement.lang = l;
    document.querySelectorAll('[data-es]').forEach(function (el) {
      if (el._en === undefined) el._en = el.innerHTML;
      el.innerHTML = l === 'es' ? el.getAttribute('data-es') : el._en;
    });
    document.querySelectorAll('.lang button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.lang === l)); });
    document.title = l === 'es' ? 'Aura – Fondos de escritorio animados e interactivos para Windows' : 'Aura – Animated, interactive wallpapers for Windows';
    buildTabs(); renderMeta();
  }
  function buildTabs() {
    tabs.innerHTML = '';
    SCENES.forEach(function (s, i) {
      var b = document.createElement('button'); b.type = 'button'; b.setAttribute('role', 'tab');
      b.setAttribute('aria-selected', String(i === cur)); b.textContent = s[lang];
      b.addEventListener('click', function () { select(i, true); });
      b.addEventListener('keydown', function (e) {
        var d = e.key === 'ArrowRight' ? 1 : e.key === 'ArrowLeft' ? -1 : 0;
        if (d) { select((cur + d + SCENES.length) % SCENES.length, active); tabs.children[cur].focus(); }
      });
      tabs.appendChild(b);
    });
    desc.textContent = SCENES[cur][lang === 'es' ? 'des' : 'den'];
  }
  function select(i, start) {
    cur = i;
    Array.prototype.forEach.call(tabs.children, function (b, k) { b.setAttribute('aria-selected', String(k === i)); });
    desc.textContent = SCENES[i][lang === 'es' ? 'des' : 'den'];
    if (start || active) load();
  }
  function load() { // only one scene runs at a time: replacing src destroys the previous page
    active = true; play.hidden = true;
    frame.title = 'Aura – ' + SCENES[cur][lang];
    frame.src = 'demo/scenes/' + SCENES[cur].id + '.html';
  }
  function unload() { if (active) { active = false; frame.src = 'about:blank'; play.hidden = false; } }
  play.addEventListener('click', load);
  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (e) { if (!e[0].isIntersecting) unload(); }, { threshold: 0.1 }).observe($('#stage'));
  }
  document.addEventListener('visibilitychange', function () { if (document.hidden) unload(); });

  var dlInfo = null;
  function renderMeta() {
    var m = $('#dl-meta'); if (!m) return;
    if (!dlInfo) { m.textContent = lang === 'es' ? 'Windows 10/11 · gratis' : 'Windows 10/11 · free'; return; }
    var mb = dlInfo.size ? (dlInfo.size / 1048576).toFixed(1) + ' MB' : '';
    m.textContent = [dlInfo.tag, mb, 'Windows 10/11'].filter(Boolean).join(' · ');
  }
  function loadRelease() {
    if (!window.fetch) return;
    fetch('https://api.github.com/repos/' + REPO + '/releases/latest', { headers: { Accept: 'application/vnd.github+json' } })
      .then(function (r) { if (!r.ok) throw 0; return r.json(); })
      .then(function (j) {
        var a = (j.assets || []).filter(function (x) { return /\.exe$/i.test(x.name); })[0];
        if (!a) return;
        $('#dl').href = a.browser_download_url;
        dlInfo = { tag: j.tag_name, size: a.size }; renderMeta();
      }).catch(function () {});
  }

  document.querySelectorAll('.lang button').forEach(function (b) {
    b.addEventListener('click', function () { try { localStorage.setItem('aura-lang', b.dataset.lang); } catch (e) {} applyLang(b.dataset.lang); });
  });
  applyLang(detect());
  loadRelease();
})();
