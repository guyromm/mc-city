<script>
  // /setup?t=<one-time token>: an admin chooses their password (token from minecraft.admin_setup_token(), single use)
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { rpc } from '$lib/api';
  import { saveSession } from '$lib/auth';
  import AuthForm from '$lib/AuthForm.svelte';
  const token = page.url.searchParams.get('t') || '';
  // drop the token from the address bar and history at once
  if (token) history.replaceState(history.state, '', '/setup');
  let pw = $state(''), pw2 = $state(''), err = $state(''), busy = $state(false);
  async function submit(e) {
    e.preventDefault(); err = '';
    if (pw !== pw2) { err = "The passwords don't match."; return; }
    busy = true;
    try {
      const r = await rpc('set_password', { p_token: token, p_password: pw }, { auth: false });
      if (r.error) { err = r.error; return; }
      saveSession(r);
      goto('/claude');
    } catch (e2) { err = e2.message; } finally { busy = false; }
  }
</script>

<svelte:head><title>Choose a password — Claude Builds</title><meta name="referrer" content="no-referrer" /></svelte:head>
<AuthForm title="Choose a password" onsubmit={submit}>
  {#if !token}
    <p class="err">This page needs the setup link you were sent. Each link works once.</p>
  {:else}
    <p class="muted">You use this password to sign in here and chat with the server's agent.</p>
    <label>New password<input type="password" autocomplete="new-password" minlength="10" bind:value={pw} required /></label>
    <label>Repeat it<input type="password" autocomplete="new-password" minlength="10" bind:value={pw2} required /></label>
    {#if err}<p class="err">{err}</p>{/if}
    <button disabled={busy}>{busy ? 'Saving…' : 'Save and sign in'}</button>
  {/if}
</AuthForm>
