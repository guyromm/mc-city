import adapter from '@sveltejs/adapter-node';
// claude-ui's components are legacy-syntax Svelte: runes are NOT forced globally, so each file is detected on its own.
export default { kit: { adapter: adapter(), alias: { '$claude-ui': '../claude-ui/web' } } };
