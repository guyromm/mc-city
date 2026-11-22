// Live player markers on the uNmINeD map (/map/index.html; scripts/render-map.sh injects this script).
// Polls PostgREST api.server_players (admins only: minecraft.is_admin(), the status worker refreshes it every ~5 s)
// with the site's admin token from localStorage. Signed-out viewers see no players and no requests beyond one 401.
(() => {
  const KEY = 'minecraft_admin', EVERY = 5000, IDLE = 30000;
  let layer = null, timer = null;

  function token() {
    try {
      const s = JSON.parse(localStorage.getItem(KEY) || 'null');
      const c = JSON.parse(atob(s.token.split('.')[1].replace(/-/g, '+').replace(/_/g, '/')));
      return c.exp && c.exp * 1000 < Date.now() ? null : s.token;
    } catch { return null; }
  }

  function draw(players) {
    // `unmined` is the viewer's top-level const in index.html (a global binding, not a window property)
    if (typeof unmined === 'undefined' || !unmined.olMap) return;
    const markers = players
      .filter((p) => !p.dim || p.dim === 'minecraft:overworld' || p.dim === 'overworld')
      .map((p) => Object.assign(Unmined.playerToMarker({ name: p.name, x: p.pos[0], z: p.pos[2] }), {
        textBackgroundColor: '#1b2117cc', font: '600 13px system-ui, sans-serif', offsetY: 18,
      }));
    const next = unmined.createMarkersLayer(markers);
    next.setZIndex(20000);
    unmined.olMap.addLayer(next);
    if (layer) unmined.olMap.removeLayer(layer);
    layer = next;
  }

  async function tick() {
    const tok = token();
    if (!tok) { if (layer) draw([]); timer = setTimeout(tick, IDLE); return; }
    try {
      const r = await fetch('/rest/server_players', { headers: { authorization: 'Bearer ' + tok } });
      if (r.ok) draw(await r.json());
      timer = setTimeout(tick, r.ok ? EVERY : IDLE);
    } catch { timer = setTimeout(tick, IDLE); }
  }

  document.addEventListener('visibilitychange', () => {   // no polling in a background tab
    clearTimeout(timer);
    if (!document.hidden) tick();
  });
  tick();
})();
