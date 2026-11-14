# Notes for Claude Code sessions on this repo

Read README.md first. It covers the layout, install, the API and how to continue the city.

The user plays as **FiscalToaster87**. The user wants:

- a persistent, continuously growing city
- the tour route updated after every addition (`tour.py upload` is staged and swaps in at the end of the current loop,
  so it never interrupts the flight)
- the HUD hidden during the tour, for immersion

Before changing anything:

1. `systemctl --user status mc-bds mc-city` and `tail ~/mc-agent/city.log`
2. `python3 ~/mc-bds/mcs.py '{"op":"ping"}'` and `'{"op":"tour_status"}'`

Working rules:

- Prefer direct `fill` builds (`send_fill` plus `verify`) over the puppet builder. The puppet is slow and pauses
  while the tour runs.
- Every build should run a scan-verify and report mismatches. Keep 0 mismatches as the bar.
- Downtown lies in core cells i∈{0,1}, j∈{0,1,2}, roughly x −44..84, z −88..104. It is hand-built, so don't overwrite
  it.
- Load an area before filling or scanning it: add a temporary tickingarea, as `city.py ensure_loaded` does. The
  server allows at most 10 persistent tickingareas, and 4 are in use: build, rotunda, park and hall.
- After any pack edit, run `scripts/deploy-pack.sh`. After significant progress, run `scripts/snapshot.sh` to commit
  the world.
- Open ideas: give apartments, houses and shops furnished interiors with `interiors.furnish_storey`, raise
  `MC_CITY_MAX_RING`, and confirm stair orientation in game.
