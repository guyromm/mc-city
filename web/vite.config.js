import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';
import path from 'node:path';
// Hardening per doc:vite-hardening (#222): R0 bind 127.0.0.1, R1 vite >= 6.2.7 (package.json), R2 explicit hosts,
// R3 minimal fs.allow (this app dir + ../claude-ui; secrets live in ~/.env, outside both), R4 wide fs.deny (keeps .env).
const here = path.dirname(new URL(import.meta.url).pathname);
export default defineConfig({
  plugins: [sveltekit()],
  envDir: here,          // no .env here: only VITE_* would ever reach the client anyway
  server: {
    // live behind nginx at minecraft.webgma.co.il (vite dev, so edits show at once); HMR over wss :443
    host: '127.0.0.1',
    strictPort: true,
    allowedHosts: ['minecraft.webgma.co.il', 'www.minecraft.webgma.co.il'],
    hmr: { protocol: 'wss', clientPort: 443 },
    fs: {
      strict: true,
      allow: [here, path.resolve(here, '../claude-ui/web')],
      deny: ['.env', '.env.*', '*.{pem,crt,key,p12,pfx}', '**/.git/**', '**/.ssh/**', '**/id_rsa*', '**/.npmrc',
             '**/.aws/**', '**/.config/**', '/proc/**', '/sys/**', '/etc/**', '/root/**', '/var/log/**']
    },
    // nginx sends /rest/ to PostgREST itself; this only matters when the dev server is hit directly
    proxy: { '/rest': { target: `http://127.0.0.1:${process.env.API_PORT || 3795}`, rewrite: (p) => p.replace(/^\/rest/, '') } }
  }
});
