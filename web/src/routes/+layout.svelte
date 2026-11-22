<script>
  import { page } from '$app/state';
  import ClaudeDock from '$claude-ui/ClaudeDock.svelte';
  import { isAdmin, getToken } from '$lib/auth';
  import { PGRST } from '$lib/api';
  let { children } = $props();
  // narration (text-to-speech) off unless the viewer turned it on
  try { if (localStorage.getItem('claude_ui_autoread') === null) localStorage.setItem('claude_ui_autoread', '0'); } catch {}
</script>

{@render children()}

<!-- claude-ui chat on every page, admins only (it re-checks isAdmin() itself) -->
<ClaudeDock pgrst={PGRST} {getToken} {isAdmin} hidden={page.url.pathname.startsWith('/claude')} />

<style>
  :global(:root) {
    --bg: #12160f; --panel: #1b2117; --panel-2: #232b1e; --line: #33402b; --text: #e8eedf; --muted: #9aa88c;
    --grass: #6fb43f; --grass-2: #4e8a2b; --dirt: #8a6239; --gold: #f2c14e; --err: #ff7a6b; --ok: #6fd36f;
    --mono: ui-monospace, 'SFMono-Regular', 'JetBrains Mono', Menlo, Consolas, monospace;
  }
  @media (prefers-color-scheme: light) {
    :global(:root) {
      --bg: #f3f1e8; --panel: #ffffff; --panel-2: #f7f5ee; --line: #dcd6c4; --text: #23281e; --muted: #6a705f;
      --grass: #3f8a1f; --grass-2: #2f6d14; --dirt: #7a5329; --gold: #b07d0a; --err: #c0392b; --ok: #2e8b3a;
    }
  }
  :global(*, *::before, *::after) { box-sizing: border-box; }
  :global(body) {
    margin: 0; background: var(--bg); color: var(--text);
    font: 16px/1.55 system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; -webkit-font-smoothing: antialiased;
  }
  :global(a) { color: var(--grass); }
  :global(button, input) { font: inherit; }
</style>
