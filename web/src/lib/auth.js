// Admin session = auth.webgma.co.il SSO only (#275/13; the local email login was removed). isAdmin() is a client-side
// hint; the server-side gate is minecraft.is_admin() (iss + aud + granted role) in every api object.
// The 15-min RS256 token (aud=minecraft) lives in httpOnly cookies; /auth/token hands it to the page. loadAuthToken() is
// awaited in +layout.js before any page renders and refetched every 5 min (the server refreshes it through auth).
const AUTH_ROLE = 'minecraft_admin';

function claims(tok) {
  try {
    const b = atob(tok.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'));
    return JSON.parse(new TextDecoder().decode(Uint8Array.from(b, (ch) => ch.charCodeAt(0))));
  } catch { return null; }
}

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

export function getToken() {
  const c = sso?.token && claims(sso.token);
  return c && c.exp * 1000 > Date.now() ? sso.token : null;
}
export const isAdmin = () => claims(getToken() || '')?.role === AUTH_ROLE;
export const session = () => (getToken() ? { name: sso.user?.name || sso.user?.username } : null);
// Signs out of this site only. The auth session itself ends at https://auth.webgma.co.il/.
export async function logout() {
  sso = null;
  try { await fetch('/auth/logout', { method: 'POST', redirect: 'manual' }); } catch {}
}
