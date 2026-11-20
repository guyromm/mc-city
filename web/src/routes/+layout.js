// client-only app: auth lives in localStorage (own login) or comes from /auth/token (auth.webgma.co.il SSO), data from PostgREST
import { loadAuthToken, keepAuthToken } from '$lib/auth';
export const ssr = false;
// awaited before any page renders, so a page that checks isAdmin()/getToken() sees an SSO sign-in on the first render
export async function load() {
  await loadAuthToken();
  keepAuthToken();
  return {};
}
