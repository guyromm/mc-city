<script>
  // /claude = the claude-ui chat with the minecraft agent (admins only; server gate is minecraft.is_admin() in api.claude_*)
  import ClaudePage from '$claude-ui/ClaudePage.svelte';
  import { isAdmin, getToken, refreshToken } from '$lib/auth';
  import { PGRST } from '$lib/api';
</script>

<svelte:head><title>Claude — Claude Builds</title></svelte:head>
<ClaudePage pgrst={PGRST} {getToken} {refreshToken} {isAdmin} loginUrl="/auth/login?next=" title={null} />
