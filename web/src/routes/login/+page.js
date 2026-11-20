// /login = sign in through auth.webgma.co.il (the only way in since #275/13; the local email login was removed).
// A full page load to the server route /auth/login, which bounces through auth and back to ?next.
import { safeNext } from '$lib/safeNext';
export function load({ url }) {
  location.replace('/auth/login?next=' + encodeURIComponent(safeNext(url.searchParams.get('next'))));
  return {};
}
