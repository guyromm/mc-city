# minecraft (minecraft.webgma.co.il)

A Minecraft Bedrock server for guy, based on github.com/guyromm/mc-city: BDS 1.26.63.1 with the world claude_build, its
behavior-pack control API (bds.py, mcs.py), the Python city builder (agent/city.py) and tour mode, plus a SvelteKit UI with
claude-ui (board #288). guy drives the server through this Claude session, from https://minecraft.webgma.co.il/claude.

**This repo IS github.com/guyromm/mc-city (public).** The home dir is the work tree, `origin` is GitHub (deploy key =
~/.ssh/id_ed25519). Never whitelist or commit anything secret. mc-city's own files (agent/, bds/, scripts/, world/,
systemd/, claude/, README.md) sit at the root next to the host's (tmux.sh, nginx.conf, sql/, web/, claude-ui).

## Layout on this host
- `~/mc-bds/` (not in git): `server/` (bedrock_server, server.properties, worlds/claude_build, behavior_packs/agent_bp),
  `backups/` (city.py's every-10-buildings tgz), `server.log`, `events.log`; `bds.py mcs.py leveldat.py packs` are
  symlinks into ~/bds. `~/mc-agent` -> ~/agent. Made by `MC_BDS=~/mc-bds scripts/install.sh --no-services`.
- `bds/server.properties` is the one that install.sh copies: allow-list=true, default-player-permission-level=member.
  Players: `mcs.py 'allowlist add NAME'`, `mcs.py 'op NAME'` (also edit ~/mc-bds/server/allowlist.json/permissions.json).
- Workers (tmux.sh): `bds` (bds.py loop), `city` (city.py run), `api` (PostgREST), `ui` (vite dev), claude-ui's relay.
  Stopping `bds`: `source tmux.sh && stop bds` closes the window; bds.py turns the SIGHUP into a graceful `stop` (world saved).

## Before changing anything in the game
1. `tmux list-windows -t minecraft`, `tail ~/mc-agent/city.log ~/mc-bds/server.log`
2. `python3 ~/mc-bds/mcs.py '{"op":"ping"}'` and `'{"op":"tour_status"}'`

## mc-city working rules (from mc-city's CLAUDE.md; guy plays as **FiscalToaster87**)
guy wants a persistent, continuously growing city; the tour route updated after every addition (`tour.py upload` is staged
and swaps in at the end of the current loop, so it never interrupts the flight); the HUD hidden during the tour.
- Prefer direct `fill` builds (`send_fill` plus `verify`) over the puppet builder (slow, pauses during the tour).
- Every build runs a scan-verify and reports mismatches. 0 mismatches is the bar.
- Downtown = core cells i∈{0,1}, j∈{0,1,2}, roughly x −44..84, z −88..104. Hand-built: never overwrite it.
- Load an area before filling or scanning it (temporary tickingarea, as `city.py ensure_loaded`). Max 10 persistent
  tickingareas; 4 in use: build, rotunda, park, hall.
- After any pack edit, `scripts/deploy-pack.sh`. After significant progress, `scripts/snapshot.sh` (commits the world: on
  dev, then the review flow below).
- Open ideas: furnished interiors for apartments/houses/shops (`interiors.furnish_storey`), raise `MC_CITY_MAX_RING`
  (env of the `city` worker), confirm stair orientation in game.

## Infrastructure (resource-manager, 2026-11-15, #288/1)
- Host gma8, unix user `minecraft`, project root = this home dir (git repo, whitelist .gitignore).
  tmux session `minecraft` (`bash tmux.sh` recreates it). mc-city's install.sh uses systemd user units; here every long-running
  process (BDS, city builder, web UI, PostgREST, claude-ui relay) is a WORKERS[...] loop in tmux.sh instead. @reboot cron starts it.
- Board handle `minecraft` (watcher window board-watch-minecraft -> minecraft:claude).
- Ports in ~/.env: UI_PORT=3794 (your SvelteKit app), API_PORT=3795 (PostgREST), RELAY_PORT=3796 (claude-ui relay).
  Bind everything to 127.0.0.1. mc-city's control API stays on 127.0.0.1:8767 (free on gma8). nginx (~/nginx.conf, symlinked
  into sites-enabled; ask resource-manager for nginx -t + reload after edits):
  https://minecraft.webgma.co.il (and www.) / -> :3794 (/claude is a route of your app), /rest/ -> :3795;
  https://api.minecraft.webgma.co.il -> :3795. A placeholder shows until something listens. TLS: webroot, auto-renew.
  Vite dev servers: doc:vite-hardening (the @fs filter already allows only ~/{web,src,node_modules,.svelte-kit,claude-ui/web}).
- The game: BDS on UDP 19132 (IPv6 19133), joined at minecraft.webgma.co.il:19132. gma8's firewall is default-deny.
  resource-manager opens 19132/19133 ONLY after you confirm the allow-list is ON. Downloading BDS means accepting Mojang's
  EULA: that acceptance is guy's.
- Postgres 17 on gma8: DB `minecraft` owned by role `minecraft` (peer auth, DBURI=postgresql:///minecraft). Roles minecraft_anon
  and minecraft_web (NOLOGIN; you hold ADMIN), minecraft_authenticator (LOGIN NOINHERIT, password in .env) for PostgREST.
  Schema `api` (yours); pgcrypto + pgjwt installed. Scratch DB `minecraft_test` (yours).
- Secrets live only in ~/.env (600): DB_AUTHENTICATOR_PASSWORD, PGRST_DB_URI, PGRST_JWT_SECRET. Never print them, never put
  them on a command line (argv is readable by every user on gma8), never share them with another project.
- Backups: ~/backup.sh daily 03:41 (cron): pg_dump -> ~/backups, restore test into minecraft_test, status in ~/.backup-status.
  Add the BDS world (worlds/claude_build) to it once BDS runs. Offsite is pending: minecraft's own Storage Box sub-account
  (guy, Hetzner Robot; #65 item 3).
- Git: ~/.ssh/id_ed25519 is minecraft's one key (GitHub deploy key with write on guyromm/mc-city).

## DB schema workflow (house convention, doc:project-skeleton)
sql/schema/ (written by pg_schema_dump.py) is the SOURCE OF TRUTH. Change the DB (psql, or write
sql/migrations/<date>-<what>.sql and psql -f it), run `python3 pg_schema_dump.py`, review `git diff sql/schema`, commit both.
Never leave a live change undumped. `sql/apply.sh --fresh` (rebuilds minecraft_test from sql/) before committing a big change.

## Board
- Handle `minecraft`. Board tasks: #288 (the project, PM board), #288/2 yours (bring-up), #119/25 (code review).
- Questions for guy: `board task update <my task> --human "..."` (Goal / options / **Recommendation** / where to answer,
  short Markdown, max 1500 chars; detail goes in a task note). Only tasks assigned to me can be updated, so make subtasks.
- Link everything: whenever I mention a task, doc, review or page to guy, give the clickable URL
  (https://board.webgma.co.il/tasks/<id>, /docs/<slug>, /reviews, https://minecraft.webgma.co.il/...).
- No thanks/acks/"noted" posts: every message wakes its recipients.

## Code review (#119/25)
Never commit straight to `main` (the default branch, = GitHub's). Commit to `dev` or `feat/<topic>`, `git push origin <b>`,
`board review submit --branch <b> --task 119/25 --title ...` (prints the review URL for guy). Merge into main only after guy
approves on https://board.webgma.co.il/reviews, push main, then `board review merged ID --sha SHA`.
