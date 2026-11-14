---
name: minecraft-city-project
description: "Bedrock Minecraft server + LLM-driven city builder on this machine (paths, services, control API, gotchas)"
metadata:
  node_type: memory
  type: project
  originSessionId: 5c706b1b-04e8-4530-b955-62e4439faf31
  modified: 2026-11-14T12:37:57.778Z
---

Started 2026-11-14. User plays Bedrock via mcpelauncher Flatpak (client 1.26.62.1); in-game player name FiscalToaster87.

- Server: BDS 1.26.63.1 in ~/mc-bds/server, world `claude_build` (superflat, Beta APIs on), wrapped by ~/mc-bds/bds.py
  (control port 127.0.0.1:8767; `~/mc-bds/mcs.py 'cmd'` or JSON `{"op":...}`). systemd user unit `mc-bds` (linger on).
- Behavior pack ~/mc-bds/packs/agent_bp (edit here, then copy to server/behavior_packs/agent_bp and run `reload`):
  ops fill/scan/players/job_* (puppet builder)/tour_* (looping fly-through, staged route swap at loop end, hud hidden).
- Builders in ~/mc-agent: tower.py, rotunda.py, park.py, hall.py (fastbuild.py <mod>), interiors.py (room detection +
  furnishing), furnish_tower.py, city.py (service `mc-city`, state city/state.json, log city.log, backups ~/mc-bds/backups),
  tour.py (route = core + hall + newest city sites; `tour.py upload`).
- Gotchas: Bedrock ids differ (brick_block, wooden_pressure_plate); scriptevent msg limit 2048 chars; no
  getDynamicProperty in early execution; `pgrep -f bedrock_server` matches itself; flatpak IBus override needed for typing.

**Why:** user wants a persistent, continuously growing city with a tour mode that updates after every addition.
**How to apply:** check `systemctl --user status mc-bds mc-city` and city.log before changing anything; keep the tour updated.
