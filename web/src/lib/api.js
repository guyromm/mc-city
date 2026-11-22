// PostgREST base: nginx proxies /rest/ -> 127.0.0.1:$API_PORT (the vite dev server proxies it too)
import { getToken } from '$lib/auth';
export const PGRST = '/rest';

const hdrs = (auth) => {
  const h = { 'content-type': 'application/json' };
  const tok = auth && getToken();
  if (tok) h.authorization = 'Bearer ' + tok;
  return h;
};
async function parse(r) {
  const txt = await r.text();
  const data = txt ? JSON.parse(txt) : null;
  if (!r.ok) throw new Error((data && data.message) || r.statusText);
  return data;
}
export const rpc = (name, body = {}, { auth = true } = {}) =>
  fetch(`${PGRST}/rpc/${name}`, { method: 'POST', headers: hdrs(auth), body: JSON.stringify(body) }).then(parse);
export const get = (path) => fetch(`${PGRST}/${path}`, { headers: hdrs(true) }).then(parse);
