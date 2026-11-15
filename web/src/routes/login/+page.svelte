<script>
  import { goto } from '$app/navigation';
  import { page } from '$app/state';
  import { rpc } from '$lib/api';
  import { saveSession } from '$lib/auth';
  import { safeNext } from '$lib/safeNext';
  import AuthForm from '$lib/AuthForm.svelte';
  let email = $state(''), password = $state(''), err = $state(''), busy = $state(false);
  async function submit(e) {
    e.preventDefault(); err = ''; busy = true;
    try {
      const r = await rpc('login', { p_email: email, p_password: password }, { auth: false });
      if (r.error) { err = r.error; return; }
      saveSession(r);
      goto(safeNext(page.url.searchParams.get('next')));
    } catch (e2) { err = e2.message; } finally { busy = false; }
  }
</script>

<svelte:head><title>Sign in — Claude Builds</title></svelte:head>
<AuthForm title="Sign in" onsubmit={submit}>
  <label>Email<input type="email" autocapitalize="none" autocomplete="username" bind:value={email} required /></label>
  <label>Password<input type="password" autocomplete="current-password" bind:value={password} required /></label>
  {#if err}<p class="err">{err}</p>{/if}
  <button disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
</AuthForm>
