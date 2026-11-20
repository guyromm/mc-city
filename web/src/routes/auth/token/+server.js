// The auth.webgma.co.il token for the browser (client-rendered app: $lib/auth's getToken() sends it to PostgREST).
// 15-min RS256, aud=minecraft; the httpOnly cookies stay server-side. Never cached.
import { json } from '@sveltejs/kit';
export const GET = ({ locals }) =>
  json({ token: locals.auth?.token ?? null, user: locals.auth?.user ?? null }, { headers: { 'cache-control': 'no-store' } });
