// Admin session: the JWT from api.login / api.set_password, kept in localStorage. isAdmin() is a client-side hint only;
// the server-side gate is minecraft.is_admin() in every api object.
const KEY = 'minecraft_admin';
const read = () => { try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch { return null; } };

function claims(tok) {
  try { return JSON.parse(atob(tok.split('.')[1].replace(/-/g, '+').replace(/_/g, '/'))); } catch { return null; }
}
export function getToken() {
  if (typeof localStorage === 'undefined') return null;
  const s = read();
  if (!s?.token) return null;
  const c = claims(s.token);
  if (!c || (c.exp && c.exp * 1000 < Date.now())) { localStorage.removeItem(KEY); return null; }
  return s.token;
}
export const isAdmin = () => !!getToken() && !!claims(getToken())?.admin;
export const session = () => (getToken() ? read() : null);
export const saveSession = (s) => localStorage.setItem(KEY, JSON.stringify(s));
export const logout = () => localStorage.removeItem(KEY);
