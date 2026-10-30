/* Aura Live: contrato común de las escenas. Una escena = un .html que carga esta librería y llama Aura.onFrame(cb).
   Estado (Aura.s), todo normalizado, independiente de la resolución:
     x,y      cursor 0..1 (crudo)      sx,sy  cursor suavizado       vx,vy  velocidad en pantallas/s
     down     botón izquierdo pulsado  clicked true SOLO en el fotograma de un clic sobre el escritorio vacío
     cpu,ram  0..1   bat 0..100   hour 0..24   night 0..1 (1 = noche cerrada)   t segundos   dt segundos del fotograma
     w,h      px de dibujo (ya multiplicados por dpr)    dpr    live true si llega por el puente (si no, usa el ratón del navegador)
   Aura.pal = 4 colores '#rrggbb' (fondo, acento, secundario, terciario); Aura.rgb(i) -> [r,g,b] 0..255; Aura.mix(a,b,t). */
(function () {
  const q = new URLSearchParams(location.search);
  const pal = (q.get('p') || '0e0e18,d97757,1d1b3a,3a1b2a').split(',').map(h => '#' + h.replace('#', ''));
  const rgb = i => { const h = pal[i]; return [1, 3, 5].map(k => parseInt(h.slice(k, k + 2), 16)); };
  const s = { x: .5, y: .5, sx: .5, sy: .5, vx: 0, vy: 0, down: false, clicked: false, cpu: .1, ram: .5, bat: 100, hour: 12, night: .5,
              t: 0, dt: .016, w: innerWidth, h: innerHeight, dpr: devicePixelRatio || 1, live: false, clicks: 0 };
  const cbs = []; let lastClicks = 0, lastT = performance.now(), px = .5, py = .5, fallbackClicks = 0;

  async function poll() {
    try {
      const j = await (await fetch('/state', { cache: 'no-store' })).json();
      s.live = true; s.x = j.x; s.y = j.y; s.down = j.down; s.clicks = j.click; s.cpu = j.cpu; s.ram = j.ram; s.bat = j.bat; s.hour = j.hour;
      setTimeout(poll, 8);
    } catch (e) { s.live = false; setTimeout(poll, 1000); }
  }
  poll();
  addEventListener('mousemove', e => { if (!s.live) { s.x = e.clientX / innerWidth; s.y = e.clientY / innerHeight; } });
  addEventListener('mousedown', e => { if (!s.live) { s.down = true; s.clicks = ++fallbackClicks; } });
  addEventListener('mouseup', () => { if (!s.live) s.down = false; });
  if (!s.live) s.hour = new Date().getHours() + new Date().getMinutes() / 60;

  function frame(now) {
    s.dt = Math.min(.05, (now - lastT) / 1000); lastT = now; s.t += s.dt;
    s.w = Math.round(innerWidth * s.dpr); s.h = Math.round(innerHeight * s.dpr);
    const k = 1 - Math.exp(-s.dt * 12); s.sx += (s.x - s.sx) * k; s.sy += (s.y - s.sy) * k;
    s.vx = (s.x - px) / Math.max(s.dt, 1e-3); s.vy = (s.y - py) / Math.max(s.dt, 1e-3); px = s.x; py = s.y;
    s.clicked = s.clicks !== lastClicks; lastClicks = s.clicks;
    s.night = .5 + .5 * Math.cos((s.hour - 13) / 24 * 2 * Math.PI);          // 0 al mediodía-tarde, 1 de madrugada
    for (const f of cbs) f(s.dt, s);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
  window.Aura = {
    s, pal, rgb, onFrame: f => cbs.push(f),
    mix: (a, b, t) => a.map((v, i) => v + (b[i] - v) * t),
    css: (c, a = 1) => `rgba(${c[0] | 0},${c[1] | 0},${c[2] | 0},${a})`,
    canvas(id = 'c') { const c = document.getElementById(id) || (document.body || document.documentElement).appendChild(Object.assign(document.createElement('canvas'), { id }));
      const fit = () => { c.width = Math.round(innerWidth * s.dpr); c.height = Math.round(innerHeight * s.dpr); }; fit(); addEventListener('resize', fit); return c; }
  };
  document.title = 'AuraLive';
  const st = document.createElement('style'); st.textContent = 'html,body{margin:0;height:100%;overflow:hidden;background:' + pal[0] + ';cursor:none}canvas{display:block;width:100vw;height:100vh}';
  document.head.appendChild(st);
})();
