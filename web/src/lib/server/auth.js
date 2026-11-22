// auth.webgma.co.il client for a SvelteKit app (server side only, no dependencies). Copy into src/lib/server/auth.js.
// Guide: doc:auth-integration (https://board.webgma.co.il/docs/auth-integration).
// Latest copy: https://auth.webgma.co.il/client/sveltekit/auth.js (source: git@git.webgma.co.il:auth client/sveltekit/auth.js)
//
// .env of the consuming system (never in git, never on a command line; read from process.env or, failing that, the file):
//   AUTH_SYSTEM=<slug registered at auth>    AUTH_CLIENT_SECRET=<from auth's admin page>
//   AUTH_CALLBACK=https://<your host>/auth/callback   (exactly as registered at auth)
//   AUTH_LIVE_CHECK=1                                  (optional: ask auth on each request, ~30 s revocation)
//
// hooks.server.js:   import { authenticate } from '#lib/server/auth.js';   // ($lib on SvelteKit 2)
//                    export const handle = ({ event, resolve }) => authenticate(event).then(() => resolve(event));
//   -> event.locals.auth = { user: {id, username, name}, role, sid, token } or null
// routes/auth/login/+server.js:     export { login as GET } from '#lib/server/auth.js';
// routes/auth/callback/+server.js:  export { callback as GET } from '#lib/server/auth.js';
// routes/auth/logout/+server.js:    export { logout as POST } from '#lib/server/auth.js';
// Gate a page:  if (!locals.auth) redirect(303, '/auth/login?next=' + encodeURIComponent(url.pathname));
// PostgREST:    fetch(api, { headers: { Authorization: 'Bearer ' + locals.auth.token } })
//               and in postgrest.conf: jwt-secret = <its current secret + auth's JWKS, see the guide>, jwt-aud = "<slug>"
import crypto from 'node:crypto';
import fs from 'node:fs';
import { redirect, error } from '@sveltejs/kit';

const AUTH = 'https://auth.webgma.co.il';
// AUTH_* from process.env, else from the .env file (AUTH_ENV_FILE, default ./.env), read once at first use: for
// production servers started from an empty environment (doc:vite-hardening R7)
let fileEnv;
function env(k) {
	if (process.env[k]) return process.env[k];
	if (!fileEnv) {
		fileEnv = {};
		try {
			for (const l of fs.readFileSync(process.env.AUTH_ENV_FILE || '.env', 'utf8').split('\n')) {
				const m = l.match(/^\s*(?:export\s+)?(AUTH_[A-Z_]+)\s*=\s*(.*?)\s*$/);
				if (m) fileEnv[m[1]] = m[2].replace(/^(['"])(.*)\1$/, '$2');
			}
		} catch { /* no file: process.env only */ }
	}
	return fileEnv[k] || '';
}
const SECURE = { path: '/', httpOnly: true, secure: true, sameSite: 'lax' };
const AT = 'auth_at', RT = 'auth_rt', ST = 'auth_state';

// ---- token verification against auth's public keys (cached 5 min, refetched on an unknown kid)
let jwks = { at: 0, keys: new Map() };
async function key(kid) {
	if (!jwks.keys.has(kid) || Date.now() - jwks.at > 300_000) {
		const r = await fetch(AUTH + '/.well-known/jwks.json');
		if (r.ok) jwks = { at: Date.now(), keys: new Map((await r.json()).keys.map((k) => [k.kid, crypto.createPublicKey({ key: k, format: 'jwk' })])) };
	}
	return jwks.keys.get(kid);
}
async function verify(token) {
	try { return await verifyOrThrow(token); } catch { return null; } // malformed cookie = not signed in
}
async function verifyOrThrow(token) {
	const [h, p, s] = String(token).split('.');
	if (!s) return null;
	const header = JSON.parse(Buffer.from(h, 'base64url'));
	if (header.alg !== 'RS256') return null;
	const k = await key(header.kid);
	if (!k || !crypto.verify('RSA-SHA256', Buffer.from(h + '.' + p), k, Buffer.from(s, 'base64url'))) return null;
	const c = JSON.parse(Buffer.from(p, 'base64url'));
	const now = Date.now() / 1000;
	if (c.iss !== AUTH || c.aud !== env('AUTH_SYSTEM') || !(c.exp > now)) return null;
	return c;
}

async function post(path, body) {
	const r = await fetch(AUTH + path, {
		method: 'POST', headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ system: env('AUTH_SYSTEM'), secret: env('AUTH_CLIENT_SECRET'), ...body })
	});
	return { status: r.status, body: await r.json().catch(() => ({})) };
}

function store(cookies, r) {
	cookies.set(AT, r.access_token, { ...SECURE, maxAge: 30 * 24 * 3600 }); // validity is the token's own exp
	if (r.refresh_token) cookies.set(RT, r.refresh_token, { ...SECURE, maxAge: 30 * 24 * 3600 });
}
function clear(cookies) { for (const c of [AT, RT]) cookies.delete(c, { path: '/' }); }

// ---- optional live check, cached 30 s per session
const live = new Map();
async function isLive(sid) {
	const hit = live.get(sid);
	if (hit && Date.now() - hit.at < 30_000) return hit.ok;
	const r = await post('/api/session_live', { sid });
	const ok = r.status === 200 ? r.body.live === true : (hit?.ok ?? true); // auth unreachable: keep the last answer
	live.set(sid, { at: Date.now(), ok });
	return ok;
}

/** Sets event.locals.auth from the cookies (refreshing through auth when the 15-min token ran out). */
export async function authenticate(event) {
	const { cookies } = event;
	event.locals.auth = null;
	let token = cookies.get(AT), c = token && (await verify(token));
	if (!c && cookies.get(RT)) {
		const r = await post('/api/refresh', { refresh_token: cookies.get(RT) });
		if (r.status === 200) { store(cookies, r.body); token = r.body.access_token; c = await verify(token); }
		else if (r.status === 401) clear(cookies); // revoked at auth: signed out here too
		// other errors (auth down): stay signed out for this request, keep the refresh handle for the next one
	}
	if (!c) return;
	if (env('AUTH_LIVE_CHECK') === '1' && !(await isLive(c.sid))) { clear(cookies); return; }
	event.locals.auth = { user: { id: c.sub, username: c.preferred_username, name: c.name }, role: c.role, sid: c.sid, token };
}

/** GET /auth/login?next=/path : bounce through auth.webgma.co.il */
export function login({ url, cookies }) {
	const state = crypto.randomBytes(16).toString('base64url');
	const next = /^\/(?![\/\\])/.test(url.searchParams.get('next') || '') ? url.searchParams.get('next') : '/';
	cookies.set(ST, state + ' ' + next, { ...SECURE, maxAge: 600 });
	const go = new URL(AUTH + '/go');
	go.searchParams.set('system', env('AUTH_SYSTEM'));
	go.searchParams.set('redirect_uri', env('AUTH_CALLBACK'));
	go.searchParams.set('state', state);
	redirect(303, go.toString()); // SvelteKit 2 (Kit 3: add { external: true })
}

/** GET /auth/callback?code=...&state=... */
export async function callback({ url, cookies }) {
	const [state, next] = (cookies.get(ST) || '').split(' ');
	cookies.delete(ST, { path: '/' });
	if (!state || url.searchParams.get('state') !== state) error(400, 'Sign-in expired, try again.');
	const r = await post('/api/exchange', { code: url.searchParams.get('code'), redirect_uri: env('AUTH_CALLBACK') });
	if (r.status !== 200) error(r.status === 403 ? 403 : 400, r.body.error === 'no_access' ? 'No access.' : 'Sign-in failed, try again.');
	store(cookies, r.body);
	redirect(303, next || '/');
}

/** POST /auth/logout : sign out of this system only (auth.webgma.co.il's "sign out everywhere" covers all). */
export function logout({ cookies }) {
	clear(cookies);
	redirect(303, '/');
}
