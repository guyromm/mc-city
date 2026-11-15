<script>
  import { onMount } from 'svelte';
  import { get } from '$lib/api';
  import { isAdmin, session, logout } from '$lib/auth';

  const HOST = 'minecraft.webgma.co.il';
  const PORT = 19132;
  let st = $state(null), players = $state([]), err = $state(''), admin = $state(false), copied = $state('');

  async function load() {
    try {
      [st] = await get('server_status');
      admin = isAdmin();
      players = admin ? await get('server_players') : [];
      err = '';
    } catch (e) { err = e.message; }
  }
  onMount(() => { load(); const t = setInterval(load, 15000); return () => clearInterval(t); });

  const ago = (t) => {
    if (!t) return '';
    const s = Math.max(0, (Date.now() - new Date(t)) / 1000);
    return s < 90 ? 'just now' : s < 5400 ? `${Math.round(s / 60)} min ago` : s < 129600 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} d ago`;
  };
  const stale = $derived(st && Date.now() - new Date(st.checked_at) > 120000);
  async function copy(v, what) {
    try { await navigator.clipboard.writeText(String(v)); copied = what; setTimeout(() => (copied = ''), 1500); } catch {}
  }
  function signOut() { logout(); admin = false; players = []; }
</script>

<svelte:head>
  <title>Claude Builds — a Minecraft city built by Claude</title>
  <meta name="description" content="A Minecraft Bedrock server with a city that Claude builds, plot by plot." />
</svelte:head>

<header>
  <div class="wrap bar">
    <a class="brand" href="/"><img src="/favicon.svg" alt="" width="22" height="22" /> Claude Builds</a>
    <nav>
      {#if admin}
        <a href="/claude">Chat with the agent</a>
        <button class="link" onclick={signOut}>Sign out</button>
      {:else}
        <a href="/login">Sign in</a>
      {/if}
    </nav>
  </div>
</header>

<main class="wrap">
  <section class="hero">
    <h1>A Minecraft city, built by Claude</h1>
    <p class="lede">
      A Bedrock server where Claude builds a city, plot by plot. Downtown has the Atrium Tower, the Rotunda Library,
      a park and a concert hall. Around it are roads, offices, apartments, houses and markets. A tour mode flies you
      through all of it.
    </p>
  </section>

  <div class="grid">
    <section class="card status" aria-live="polite">
      <h2>Server</h2>
      {#if err}
        <p class="err">Couldn't load the status: {err}</p>
      {:else if !st}
        <p class="muted">Loading…</p>
      {:else}
        <div class="state">
          <span class="dot" class:on={st.online && !stale}></span>
          <strong>{st.online && !stale ? 'Online' : 'Offline'}</strong>
          {#if st.online && st.online_since && !stale}<span class="muted">· up since {ago(st.online_since)}</span>{/if}
        </div>
        <dl>
          <div><dt>Players</dt><dd>{st.online ? st.players_online : '–'}{st.max_players ? ` / ${st.max_players}` : ''}</dd></div>
          <div><dt>Buildings</dt><dd>{st.plots_built ?? '–'}</dd></div>
          <div><dt>Version</dt><dd>{st.version ?? '1.26.63'}</dd></div>
        </dl>
        <p class="muted small">Checked {ago(st.checked_at)}</p>
      {/if}
    </section>

    <section class="card join">
      <h2>How to join</h2>
      <ol>
        <li>Open <strong>Minecraft Bedrock</strong> on version <strong>1.26.6x</strong> (iPhone/iPad, Android, Windows).</li>
        <li>Go to <em>Play → Servers → Add Server</em>.</li>
        <li>
          Enter the address and port:
          <div class="addr">
            <button class="chip" onclick={() => copy(HOST, 'host')} title="Copy">{HOST}<span>{copied === 'host' ? 'copied' : 'copy'}</span></button>
            <button class="chip" onclick={() => copy(PORT, 'port')} title="Copy">{PORT}<span>{copied === 'port' ? 'copied' : 'copy'}</span></button>
          </div>
        </li>
      </ol>
      <p class="console">
        <strong>PlayStation, Xbox or Switch?</strong> Consoles have no "Add Server". In Minecraft, open
        <em>Play → Friends → Add Friend</em>, add <button class="chip inline" onclick={() => copy('AiryCargo2793', 'tag')} title="Copy">AiryCargo2793<span>{copied === 'tag' ? 'copied' : 'copy'}</span></button>,
        then join <em>Claude Builds</em> from the Friends tab. Online play on consoles needs the console's own subscription (PS Plus, Game Pass, Switch Online).
      </p>
      <p class="muted small">Everyone is welcome as a visitor: walk and fly around the city. Building is reserved for the city's builders.</p>
    </section>

    <section class="card wide map">
      <div class="maphead">
        <h2>Map</h2>
        <a href="/map/index.html" target="_blank" rel="noopener">Open full screen ↗</a>
      </div>
      <iframe src="/map/index.html" title="Top-down map of the city" loading="lazy"></iframe>
      <p class="muted small">Drag to move, scroll or pinch to zoom. Redrawn every hour from the live world.</p>
    </section>

    {#if admin}
      <section class="card wide">
        <h2>Online now</h2>
        {#if !players.length}
          <p class="muted">Nobody is on the server.</p>
        {:else}
          <table>
            <thead><tr><th>Player</th><th>Position</th><th>Dimension</th></tr></thead>
            <tbody>
              {#each players as p}
                <tr><td>{p.name}</td><td class="mono">{p.pos?.join(', ')}</td><td>{p.dim?.replace('minecraft:', '')}</td></tr>
              {/each}
            </tbody>
          </table>
        {/if}
        <p class="muted small">
          Signed in as {session()?.name ?? session()?.email}. Building, tours, players and restarts:
          ask in the <a href="/claude">agent chat</a>.
        </p>
      </section>
    {/if}
  </div>
</main>

<footer class="wrap muted small">
  Based on <a href="https://github.com/guyromm/mc-city">mc-city</a>. Not an official Minecraft product. Not approved by or
  associated with Mojang or Microsoft.
</footer>

<style>
  .wrap { max-width: 980px; margin: 0 auto; padding: 0 16px; }
  header { border-bottom: 1px solid var(--line); background: var(--panel); }
  .bar { display: flex; align-items: center; justify-content: space-between; height: 56px; gap: 12px; }
  .brand { display: flex; align-items: center; gap: 10px; font-weight: 700; color: var(--text); text-decoration: none; letter-spacing: .2px; }
  .brand img { image-rendering: pixelated; border-radius: 3px; }
  nav { display: flex; gap: 16px; align-items: center; font-size: 15px; }
  nav a { text-decoration: none; }
  .link { background: none; border: 0; padding: 0; color: var(--muted); cursor: pointer; }
  .link:hover { color: var(--text); }

  .hero { padding: 48px 0 28px; }
  h1 { font-size: clamp(28px, 5vw, 42px); line-height: 1.15; margin: 0 0 14px; letter-spacing: -.5px; text-wrap: balance; }
  .lede { color: var(--muted); max-width: 62ch; margin: 0; font-size: 17px; }

  .grid { display: grid; grid-template-columns: 1fr 1.3fr; gap: 16px; }
  .card { background: var(--panel); border: 1px solid var(--line); border-radius: 12px; padding: 20px 22px; min-width: 0; }
  .wide { grid-column: 1 / -1; }
  .map { padding-bottom: 14px; }
  .maphead { display: flex; justify-content: space-between; align-items: baseline; gap: 12px; }
  .maphead a { font-size: 14px; text-decoration: none; }
  .map iframe { display: block; width: 100%; height: clamp(320px, 60vh, 560px); border: 1px solid var(--line);
                border-radius: 8px; background: #6f9144; }
  .map p { margin: 10px 0 0; }
  h2 { font-size: 13px; text-transform: uppercase; letter-spacing: 1px; color: var(--muted); margin: 0 0 14px; font-weight: 600; }

  .state { display: flex; align-items: center; gap: 8px; font-size: 20px; }
  .dot { width: 11px; height: 11px; border-radius: 2px; background: var(--muted); opacity: .6; }
  .dot.on { background: var(--ok); opacity: 1; box-shadow: 0 0 0 4px color-mix(in srgb, var(--ok) 20%, transparent); }
  dl { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 18px 0 10px; }
  dl div { background: var(--panel-2); border: 1px solid var(--line); border-radius: 8px; padding: 10px 12px; }
  dt { font-size: 12px; color: var(--muted); }
  dd { margin: 2px 0 0; font: 600 18px/1.3 var(--mono); font-variant-numeric: tabular-nums; white-space: nowrap; }
  @media (max-width: 420px) { dl { gap: 8px; } dl div { padding: 9px 10px; } dd { font-size: 16px; } }

  ol { margin: 0; padding-left: 20px; }
  li { margin-bottom: 8px; }
  .addr { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
  .chip { display: inline-flex; align-items: center; gap: 10px; background: var(--panel-2); border: 1px solid var(--line);
          border-radius: 8px; padding: 7px 10px; color: var(--text); font: 600 15px var(--mono); cursor: pointer; max-width: 100%; overflow-wrap: anywhere; }
  .chip span { font: 500 11px system-ui, sans-serif; color: var(--muted); text-transform: uppercase; letter-spacing: .6px; }
  .chip:hover { border-color: var(--grass-2); }
  .chip.inline { padding: 2px 8px; font-size: 14px; vertical-align: baseline; }
  .console { margin: 16px 0 0; padding-top: 14px; border-top: 1px solid var(--line); font-size: 15px; }

  table { width: 100%; border-collapse: collapse; font-size: 15px; }
  th, td { text-align: left; padding: 8px 6px; border-bottom: 1px solid var(--line); }
  th { font-size: 12px; color: var(--muted); font-weight: 600; }
  .mono { font-family: var(--mono); font-variant-numeric: tabular-nums; }

  .muted { color: var(--muted); }
  .small { font-size: 13px; }
  .err { color: var(--err); }
  footer.wrap { padding-top: 40px; padding-bottom: 32px; }

  @media (max-width: 720px) {
    .grid { grid-template-columns: 1fr; }
    .hero { padding: 32px 0 20px; }
  }
</style>
