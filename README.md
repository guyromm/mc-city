# Claude Builds — an LLM-built Minecraft Bedrock city

A Bedrock Dedicated Server world (`claude_build`, superflat) in which Claude built a downtown core and a procedurally
grown city. The downtown has:

- the Atrium Tower, furnished
- the Rotunda Library, with a skybridge to the tower
- a park
- a Concert Hall with a boulevard

Around it are about 200 city plots of roads, offices, apartments, houses, markets, parks and utilities. A behavior-pack
script exposes a control API. A looping **tour mode** flies the player through the city, and the route updates after
every new building.

```
bds/                    server side
  bds.py                runs bedrock_server; control port 127.0.0.1:8767 (raw console lines or JSON ops)
  mcs.py                CLI client:  mcs.py 'say hi'   |   mcs.py '{"op":"ping"}'
  leveldat.py           level.dat patcher (used once to enable Beta APIs/experiments on the world)
  server.properties     creative, peaceful, cheats, allow-list on, default permission = visitor, view-distance 16
  packs/agent_bp/       behavior pack (Script API @minecraft/server 2.12.0-beta)
agent/                  builders (Python 3, stdlib only; wsbridge.py needs `websockets`)
  tower.py              Atrium Tower + shared lib: Model, boxes(), Conn, send_fill, verify, ASC stair map
  rotunda.py park.py hall.py   downtown modules     (fastbuild.py <module> builds & verifies one)
  furnish_tower.py interiors.py   room detection + furnishing
  puppet.py             streams jobs to the in-game "puppet" builder (the player physically places blocks)
  city.py               procedural city service (state in agent/city/state.json)
  tour.py               tour route builder/uploader
  mc.py wsbridge.py     early experiment: client /connect websocket bridge (not needed any more)
world/claude_build/     snapshot of the map (LevelDB), made with scripts/snapshot.sh
systemd/                user units mc-bds.service, mc-city.service
scripts/                install.sh, snapshot.sh, deploy-pack.sh
claude/                 Claude Code memory note(s) about the project
CLAUDE.md               instructions for a Claude Code session continuing the work
```

## Instantiate on a machine

You need a Linux x86_64 machine with `python3`, `curl`, `unzip` and systemd user services.

```bash
git clone <this repo> ~/mc-city      # any path works; this one is used below
~/mc-city/scripts/install.sh         # downloads BDS 1.26.63.1, installs world + pack, links code, starts services
```

What `install.sh` does:

- creates `~/mc-bds/server`, with the server, `server.properties`, the world and `behavior_packs/agent_bp`
- symlinks `~/mc-bds/{bds.py,mcs.py,leveldat.py,packs}` and `~/mc-agent` back to this repo, so the repo is the live
  source
- installs and enables the `mc-bds` and `mc-city` user services, and enables linger so they run without a login

Options and notes:

- An existing world is never replaced unless you pass `--force-world`.
- `--no-services` installs everything but leaves the services off.
- To use another server version, set `BDS_VERSION=x.y.z`. The world needs a version of 1.26.63 or later that still
  provides `@minecraft/server` 2.12.0-beta. If the pack fails to load, change its `manifest.json` dependency to a
  module version the server lists.
- The `mc-bds` user is not required. The paths are `$HOME`-relative, and the units use `%h`.

Check that it's running:

```bash
systemctl --user status mc-bds mc-city
python3 ~/mc-bds/mcs.py '{"op":"ping"}'
python3 ~/mc-bds/mcs.py list
```

## Join

Use any Bedrock client on a compatible version (1.26.6x), connecting to the host's IP on **port 19132/UDP**. That
means the LAN IP, a Tailscale IP, or a port-forward. On Linux the client used here was the mcpelauncher Flatpak
`io.mrarm.mcpelauncher`. If typing in chat does not work there, disable IBus for it:
`flatpak override --user --env=XMODIFIERS=@im=none --env=GTK_IM_MODULE=simple io.mrarm.mcpelauncher`.

> **Security:** `allow-list=true` and `default-player-permission-level=visitor`: only players in `allowlist.json` can
> join, and they can look but not build. Add players with `mcs.py 'allowlist add NAME'` and make yourself operator with
> `mcs.py 'op NAME'`. (Earlier snapshots shipped `allow-list=false` + `operator`: anyone reaching the port became an
> operator.)

## Tour mode

```bash
python3 ~/mc-agent/tour.py upload            # rebuild route from state.json and upload (staged; swaps at loop end)
python3 ~/mc-agent/tour.py start PLAYERNAME  # start (also hides HUD);  tour.py stop | status
```

In game you can also type `/scriptevent agent:tour_start {"player":"NAME"}`. To exit, **hold crouch for 2 s**. The tour
state persists across restarts, and it resumes when that player is online.

## Continue construction

The city service builds ring by ring around downtown, up to `MAX_RING` (default 6, which is now complete). To grow
further, edit `systemd/mc-city.service` and uncomment or raise `Environment=MC_CITY_MAX_RING=8`. Then:

```bash
cp ~/mc-city/systemd/mc-city.service ~/.config/systemd/user/ && systemctl --user daemon-reload && systemctl --user restart mc-city
tail -f ~/mc-agent/city.log
```

Each new plot goes through these steps:

1. roads on the plot's edges, then a building whose type depends on its distance from downtown
2. a scan-verify and a repair pass
3. a record in `agent/city/state.json`
4. a tour upload and a chat announcement
5. every 10 buildings, a backup to `~/mc-bds/backups`

Other commands:

```bash
python3 ~/mc-agent/city.py status                 # list built plots
python3 ~/mc-agent/city.py one I J [type]         # build one cell now (office|apartments|houses|market|park|utility)
systemctl --user stop mc-city                     # pause;  start to resume
```

The grid: road centrelines are at x = −44 + 64·i and z = −88 + 64·j. The core cells i∈{0,1}, j∈{0,1,2} are downtown
and are never rebuilt.

## Control API (behavior pack ops)

Send these as JSON through `mcs.py` / `tower.Conn().req({...})`. The server runs them as `scriptevent agent:<op>`, and
the reply is matched by id.

| op | args | purpose |
|---|---|---|
| `ping`, `players` | | health, online players |
| `fill` | `ops: [[x1,y1,z1,x2,y2,z2,block,states?], ...]` | bulk block placement (`dimension.fillBlocks`) |
| `scan` | box | palette and run-length rows, for verification (reports `unloaded` chunks) |
| `cmd` | `cmd` | run a slash command as the server |
| `job_add/status/clear/pause` | | puppet builder: the player teleports, aims and places blocks |
| `tour_set/start/stop/status` | `wps`, `reset`, `save`, `player` | tour route and playback |

There is a 2048-character limit per scriptevent message, so large payloads are chunked (`send_fill`,
`tour.upload`). Areas must be loaded before a fill or scan: builders add a temporary `tickingarea`.

## Snapshot and backup

```bash
~/mc-city/scripts/snapshot.sh "message"   # consistent live copy of the world into world/ (save hold/query/resume) + commit
```

Edits to `agent/` and `bds/` are already live, because of the symlinks. Commit them as normal. After editing
`bds/packs/agent_bp/scripts/main.js`, run `scripts/deploy-pack.sh` to copy it into the server and run `reload`.

## Gotchas

- Bedrock block ids differ from Java: `brick_block`, `wooden_pressure_plate`. Check unknown ids with a 1-block `fill`
  first. `city.py` probes its palette at startup.
- Script API: `getDynamicProperty` is not available during early execution, so state loads via `system.runTimeout`.
- `pgrep -f bedrock_server` matches itself; use `systemctl --user status mc-bds` instead.
- Stair facing in `tower.ASC` has never been confirmed by walking the stairs in game.
