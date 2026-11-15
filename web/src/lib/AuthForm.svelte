<script>
  // shared shell of /login and /setup
  let { title, children, onsubmit } = $props();
</script>

<main>
  <form {onsubmit}>
    <a class="brand" href="/"><img src="/favicon.svg" alt="" width="22" height="22" /> Claude Builds</a>
    <h1>{title}</h1>
    {@render children()}
  </form>
</main>

<style>
  main { min-height: 100dvh; display: grid; place-items: center; padding: 16px; }
  form { width: 100%; max-width: 380px; background: var(--panel); border: 1px solid var(--line); padding: 26px 22px; border-radius: 12px; }
  .brand { display: flex; align-items: center; gap: 10px; font-weight: 700; color: var(--text); text-decoration: none; }
  .brand img { image-rendering: pixelated; border-radius: 3px; }
  h1 { font-size: 22px; margin: 18px 0 16px; }
  form :global(label) { display: block; font-size: 14px; color: var(--muted); margin-bottom: 12px; }
  form :global(input) { width: 100%; padding: 11px 12px; border: 1px solid var(--line); border-radius: 8px; margin-top: 4px;
                        font-size: 16px; background: var(--panel-2); color: var(--text); }
  form :global(input:focus) { outline: 2px solid var(--grass-2); outline-offset: 1px; }
  form :global(button) { width: 100%; padding: 12px; border: 0; border-radius: 8px; background: var(--grass-2); color: #fff;
                         font-weight: 600; font-size: 16px; cursor: pointer; margin-top: 4px; }
  form :global(button:disabled) { opacity: .6; cursor: default; }
  form :global(.err) { color: var(--err); font-size: 14px; }
  form :global(.muted) { color: var(--muted); font-size: 14px; }
</style>
