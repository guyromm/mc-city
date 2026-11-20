// Admin session, two ways in. isAdmin() is a client-side hint only; the server-side gate is minecraft.is_admin() in every
// api object.
//  1. Own login: the JWT from api.login / api.set_password (HS256, ours), kept in localStorage.
//  2. auth.webgma.co.il SSO (#275/13, doc:auth-integration): the 15-min RS256 token (aud=minecraft) lives in httpOnly
//     cookies; /auth/token hands it to the page. loadAuthToken() is awaited in +layout.js before any page renders, and
//     refetched every 5 min (the server refreshes it through auth when it runs out).
const KEY = 'minecraft_admin';
const AUTH_ROLE = 'minecraft_web';
const read = () => { try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch { return null; } };

function claims(tok) {
  try {
    const b = atob(tok.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(new TextDecoder().decode(Uint8Array.from(b, (ch) => ch.charCodeAt(0))));
  } catch { return null; }
}
const fresh = (c) => c && !(c.exp && c.exp * 1000 < Date.now());

let sso = null; // { token, user } from /auth/token, or null
export async function loadAuthToken() {
  try {
    const r = await fetch('/auth/token', { cache: 'no-store' });
    const j = r.ok ? await r.json() : null;
    sso = j?.token ? j : null;
  } catch { /* offline: keep the last one until it expires */ }
  return sso;
}
let timer;
export function keepAuthToken() {
  if (typeof window === 'undefined' || timer) return;
  timer = setInterval(loadAuthToken, 5 * 60_000);
}

function localToken() {
  if (typeof localStorage === 'undefined') return null;
  const s = read();
  if (!s?.token) return null;
  if (!fresh(claims(s.token))) { localStorage.removeItem(KEY); return null; }
  return s.token;
}
const ssoToken = () => (sso?.token && fresh(claims(sso.token)) ? sso.token : null);

export const getToken = () => localToken() || ssoToken();
export const isAdmin = () => !!claims(localToken() || '')?.admin || claims(ssoToken() || '')?.role === AUTH_ROLE;
export const session = () => {
  if (localToken()) return read();
  if (ssoToken()) return { name: sso.user?.name || sso.user?.username, via: 'auth' };
  return null;
};
export const saveSession = (s) => localStorage.setItem(KEY, JSON.stringify(s));
// Signs out of this site only (both ways in). The auth session itself ends at https://auth.webgma.co.il/.
export async function logout() {
  localStorage.removeItem(KEY);
  if (sso) { sso = null; try { await fetch('/auth/logout', { method: 'POST', redirect: 'manual' }); } catch {} }
}
