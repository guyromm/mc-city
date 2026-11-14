// Claude Agent bridge. Driven via `/scriptevent agent:<op> <json>` from the server console.
// Replies are printed as single lines: "AGENT <id> <json>" so the host wrapper can match them.
import { world, system, BlockPermutation, BlockVolume, ItemStack } from "@minecraft/server";

const puppet = { queue: [], cur: null, done: 0, speed: 0.8, center: [0, 0], player: null, paused: false, errors: [], lastItem: null };

const out = (id, obj) => console.warn(`AGENT ${id} ${JSON.stringify(obj)}`);
const dim = (name) => world.getDimension(name ?? "overworld");
const short = (t) => (t.startsWith("minecraft:") ? t.slice(10) : t);

function perm(type, states) {
  const t = type.includes(":") ? type : `minecraft:${type}`;
  return BlockPermutation.resolve(t, states ?? undefined);
}

const ops = {
  ping: () => ({ pong: true, tick: system.currentTick }),

  players: () =>
    world.getAllPlayers().map((p) => ({
      name: p.name,
      pos: [p.location.x, p.location.y, p.location.z].map((v) => Math.round(v * 10) / 10),
      dim: p.dimension.id,
    })),

  // {ops:[[x1,y1,z1,x2,y2,z2,"stone",{states}?], ...], dim?}
  fill: (a) => {
    const d = dim(a.dim);
    let placed = 0;
    const errors = [];
    for (const [i, op] of a.ops.entries()) {
      const [x1, y1, z1, x2, y2, z2, type, states] = op;
      try {
        const p = perm(type, states);
        const vol = new BlockVolume({ x: x1, y: y1, z: z1 }, { x: x2, y: y2, z: z2 });
        if (d.fillBlocks) {
          const r = d.fillBlocks(vol, p);
          placed += typeof r === "number" ? r : r.getCapacity ? r.getCapacity() : 0;
        } else {
          for (const loc of vol.getBlockLocationIterator()) { d.getBlock(loc)?.setPermutation(p); placed++; }
        }
      } catch (e) {
        errors.push({ i, err: String(e) });
      }
    }
    return { placed, errors };
  },

  // {from:[x,y,z], to:[x,y,z], dim?} -> palette + per-layer rows (RLE "idx*count")
  scan: (a) => {
    const d = dim(a.dim);
    const [x1, y1, z1] = a.from.map((v, i) => Math.min(v, a.to[i]));
    const [x2, y2, z2] = a.from.map((v, i) => Math.max(v, a.to[i]));
    const palette = [], index = new Map(), layers = [];
    let unloaded = 0;
    for (let y = y1; y <= y2; y++) {
      const rows = [];
      for (let z = z1; z <= z2; z++) {
        const runs = [];
        let prev = -1, n = 0;
        for (let x = x1; x <= x2; x++) {
          let key;
          try {
            const b = d.getBlock({ x, y, z });
            if (!b) { key = "?"; unloaded++; }
            else {
              const st = b.permutation.getAllStates();
              const ks = Object.keys(st);
              key = short(b.typeId) + (ks.length ? JSON.stringify(st) : "");
            }
          } catch { key = "?"; unloaded++; }
          if (!index.has(key)) { index.set(key, palette.length); palette.push(key); }
          const k = index.get(key);
          if (k === prev) n++; else { if (n) runs.push(n > 1 ? `${prev}*${n}` : `${prev}`); prev = k; n = 1; }
        }
        runs.push(n > 1 ? `${prev}*${n}` : `${prev}`);
        rows.push(runs.join(","));
      }
      layers.push(rows);
    }
    return { origin: [x1, y1, z1], size: [x2 - x1 + 1, y2 - y1 + 1, z2 - z1 + 1], palette, layers, unloaded };
  },

  // ---- puppet builder: move a real player to each job, face it, hold the block, place it
  // {player, items:[[x1,y1,z1,x2,y2,z2,type,states?], ...], speed?, center?:[x,z]}
  job_add: (a) => {
    if (a.speed) puppet.speed = a.speed;
    if (a.center) puppet.center = a.center;
    if (a.player) puppet.player = a.player;
    for (const it of a.items) puppet.queue.push(it);
    return { queued: puppet.queue.length, done: puppet.done };
  },
  job_status: () => ({ queued: puppet.queue.length, done: puppet.done, active: !!puppet.cur, paused: puppet.paused, player: puppet.player, errors: puppet.errors.slice(-5) }),
  job_clear: () => { puppet.queue.length = 0; puppet.cur = null; return { cleared: true }; },
  job_pause: (a) => { puppet.paused = !!a.paused; return { paused: puppet.paused }; },

  // run arbitrary commands as the world: {cmds:["..."]}
  cmd: (a) => a.cmds.map((c) => { try { return dim(a.dim).runCommand(c).successCount; } catch (e) { return String(e); } }),
};

system.afterEvents.scriptEventReceive.subscribe((ev) => {
  if (!ev.id.startsWith("agent:")) return;
  const op = ev.id.slice(6);
  let args = {};
  try { args = ev.message ? JSON.parse(ev.message) : {}; } catch (e) { return out("?", { error: "bad json: " + e }); }
  const id = args.id ?? "0";
  const fn = ops[op];
  if (!fn) return out(id, { error: `unknown op ${op}` });
  try { out(id, { ok: true, result: fn(args) }); } catch (e) { out(id, { error: String(e) }); }
});

world.afterEvents.playerSpawn.subscribe((ev) => {
  if (ev.initialSpawn) out("event", { join: ev.player.name });
});
world.afterEvents.playerLeave?.subscribe((ev) => out("event", { leave: ev.playerName }));
// chat is beta-only; subscribe when available
try {
  world.afterEvents.chatSend?.subscribe((ev) => out("event", { chat: ev.sender.name, msg: ev.message }));
} catch {}


// ---- puppet tick loop
function vantage(it) {
  const [x1, y1, z1, x2, y2, z2] = it;
  const c = { x: (x1 + x2) / 2 + 0.5, y: Math.max(y1, y2) + 1, z: (z1 + z2) / 2 + 0.5 };
  let dx = c.x - puppet.center[0], dz = c.z - puppet.center[1];
  const l = Math.hypot(dx, dz);
  if (l > 0.5) { dx /= l; dz /= l; } else { dx = 0; dz = 1; }
  return { look: c, pos: { x: c.x + dx * 3.5, y: c.y + 1.2, z: c.z + dz * 3.5 } };
}
system.runInterval(() => {
  if (puppet.paused || (!puppet.cur && !puppet.queue.length)) return;
  const p = world.getAllPlayers().find((q) => !puppet.player || q.name === puppet.player);
  if (!p) return;
  if (!puppet.cur) { const it = puppet.queue.shift(); puppet.cur = { it, ...vantage(it) }; }
  const { it, pos, look } = puppet.cur;
  const l = p.location, d = { x: pos.x - l.x, y: pos.y - l.y, z: pos.z - l.z };
  const dist = Math.hypot(d.x, d.y, d.z);
  const s = puppet.speed;
  const next = dist <= s || dist > 48 ? pos : { x: l.x + (d.x / dist) * s, y: l.y + (d.y / dist) * s, z: l.z + (d.z / dist) * s };
  try { p.teleport(next, { facingLocation: look }); } catch (e) { puppet.errors.push("tp " + e); }
  const type = it[6];
  if (puppet.lastItem !== type) {
    puppet.lastItem = type;
    try {
      const inv = p.getComponent("minecraft:inventory").container;
      inv.setItem(p.selectedSlotIndex, new ItemStack(type.includes(":") ? type : "minecraft:" + type, 1));
    } catch {}
  }
  if (next !== pos) return;
  try {
    const [x1, y1, z1, x2, y2, z2, , states] = it;
    p.dimension.fillBlocks(new BlockVolume({ x: x1, y: y1, z: z1 }, { x: x2, y: y2, z: z2 }), perm(type, states));
    try { p.dimension.spawnParticle("minecraft:villager_happy", look); } catch {}
  } catch (e) { puppet.errors.push(`${JSON.stringify(it)}: ${e}`); }
  puppet.done++; puppet.cur = null;
}, 1);


// ---- tour mode: Catmull-Rom flight through waypoints [x,y,z,lx,ly,lz,ticks], loops; sneak to exit
const tour = { wps: [], on: false, player: null, seg: 0, t: 0 };
system.runTimeout(() => {
  try { const saved = world.getDynamicProperty("tour"); if (saved) tour.wps = JSON.parse(saved); } catch (e) { tour.err = "load " + e; }
  try { const st = world.getDynamicProperty("tour_state"); if (st) { const o = JSON.parse(st); tour.on = o.on; tour.player = o.player; if (tour.on) puppet.paused = true; } } catch (e) { tour.err = "load " + e; }
}, 20);
const saveState = () => { try { world.setDynamicProperty("tour_state", JSON.stringify({ on: tour.on, player: tour.player })); } catch {} };
ops.tour_set = (a) => {
  // staged upload: chunks go to tour.next; on save it becomes live at the end of the current loop
  if (a.reset) tour.next = [];
  tour.next.push(...a.wps);
  if (a.save) {
    world.setDynamicProperty("tour", JSON.stringify(tour.next));
    if (!tour.on || tour.wps.length < 2) { tour.wps = tour.next; tour.next = null; } else tour.swap = true;
  }
  return { staged: tour.next ? tour.next.length : 0, live: tour.wps.length };
};
ops.tour_start = (a) => {
  const p = world.getAllPlayers().find((q) => !a.player || q.name === a.player);
  if (!p || tour.wps.length < 2) return { error: "no player or no tour" };
  tour.player = p.name; tour.on = true; tour.seg = 0; tour.t = 0; puppet.paused = true; saveState();
  try { p.runCommand("gamemode creative @s"); p.runCommand("ability @s mayfly true"); p.runCommand("hud @s hide all"); } catch {}
  p.onScreenDisplay?.setActionBar?.("§bTour mode§r — hold crouch 2s to exit");
  return { started: p.name, n: tour.wps.length };
};
ops.tour_status = () => ({ swap_pending: !!tour.swap, on: tour.on, player: tour.player, seg: tour.seg, t: tour.t, n: tour.wps.length, err: tour.err });
ops.tour_stop = () => { try { world.getAllPlayers().find((q) => q.name === tour.player)?.runCommand("hud @s reset all"); } catch {}
  tour.on = false; puppet.paused = false; saveState(); return { stopped: true }; };
const cr = (p0, p1, p2, p3, t) => {
  const t2 = t * t, t3 = t2 * t;
  return 0.5 * (2 * p1 + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3);
};
system.runInterval(() => {
  if (!tour.on) return;
  const p = world.getAllPlayers().find((q) => q.name === tour.player);
  if (!p) return;  // wait for the player to (re)join
  tour.sneak = p.isSneaking ? (tour.sneak ?? 0) + 1 : 0;
  if (tour.sneak > 40) { try { p.runCommand("hud @s reset all"); } catch {} tour.sneak = 0; tour.on = false; tour.err = "exited by sneak"; puppet.paused = false; saveState(); p.onScreenDisplay?.setActionBar?.("Tour ended"); return; }
  const W = tour.wps, n = W.length;
  if (n < 2) return;
  if (tour.seg >= n) { tour.seg = 0; tour.t = 0; }
  const i = tour.seg;
  const a = W[(i - 1 + n) % n], b = W[i], c = W[(i + 1) % n], d = W[(i + 2) % n];
  const f = Math.min(1, tour.t / Math.max(1, c[6]));
  const pos = { x: cr(a[0], b[0], c[0], d[0], f), y: cr(a[1], b[1], c[1], d[1], f), z: cr(a[2], b[2], c[2], d[2], f) };
  const look = { x: b[3] + (c[3] - b[3]) * f, y: b[4] + (c[4] - b[4]) * f, z: b[5] + (c[5] - b[5]) * f };
  try { p.teleport(pos, { facingLocation: look }); } catch (e) { tour.err = String(e); }
  if (++tour.t > c[6]) { tour.t = 0; tour.seg = (i + 1) % n; if (tour.seg === 0 && tour.swap) { tour.wps = tour.next; tour.next = null; tour.swap = false; } }
}, 1);

system.run(() => out("event", { ready: true }));
