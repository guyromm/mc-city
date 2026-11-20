// client-only app: the admin token comes from /auth/token (auth.webgma.co.il SSO), data from PostgREST
import { loadAuthToken, keepAuthToken } from '$lib/auth';
export const ssr = false;
// awaited before any page renders, so a page that checks isAdmin()/getToken() sees an SSO sign-in on the first render
export async function load() {
  await loadAuthToken();
  keepAuthToken();
  return {};
}
// the removed local login kept its token here; drop it (it no longer grants anything)
try { localStorage.removeItem('minecraft_admin'); } catch {}
