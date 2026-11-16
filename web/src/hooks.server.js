// /map/* is the hourly uNmINeD render (scripts/render-map.sh -> web/map/), served from disk on every request:
// it lives outside static/ because adapter-node indexes static files once at startup, and the map is replaced hourly.
import { readFile } from 'node:fs/promises';
import path from 'node:path';

const MAP = path.resolve(process.env.MAP_DIR || path.join(process.cwd(), 'map'));
const TYPES = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.webp': 'image/webp',
  '.png': 'image/png', '.json': 'application/json', '.txt': 'text/plain; charset=utf-8', '.svg': 'image/svg+xml', '.ico': 'image/x-icon' };

export async function handle({ event, resolve }) {
  const p = event.url.pathname;
  if (p === '/map') return new Response(null, { status: 308, headers: { location: '/map/' } });
  if (!p.startsWith('/map/')) return resolve(event);
  let rel;
  try { rel = decodeURIComponent(p.slice(5)); } catch { return new Response('bad path', { status: 400 }); }
  if (rel === '' || rel.endsWith('/')) rel += 'index.html';
  const f = path.resolve(MAP, rel);
  if (!f.startsWith(MAP + path.sep) || rel.includes('\0')) return new Response('not found', { status: 404 });
  try {
    const body = await readFile(f);
    return new Response(body, { headers: { 'content-type': TYPES[path.extname(f)] || 'application/octet-stream',
      'cache-control': 'no-cache', 'x-content-type-options': 'nosniff' } });
  } catch { return new Response('not found', { status: 404 }); }
}
