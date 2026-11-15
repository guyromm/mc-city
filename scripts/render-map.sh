#!/usr/bin/env bash
# Render the world into a static web map (uNmINeD CLI, OpenLayers viewer) at web/static/map/ -> https://<site>/map/
#   scripts/render-map.sh            (the `map` worker runs it every MAP_EVERY seconds; ~10 s for the whole city)
# Reads a consistent COPY of the live world (scripts/world-backup.sh), never the live files.
# Post-process: BDS keeps no terrain for chunks that are still untouched generated superflat (it regenerates them),
# and uNmINeD draws those as empty: pure black without shadows, the background colour (rendered magenta) with them.
# Nothing else on this map is either, so both are repainted lawn green, as is the endless flat land around the city.
# uNmINeD: closed source, free for non-commercial use (unmined.net/license), ~/.local/lib/unmined (not in git).
set -euo pipefail
REPO="$(cd "$(dirname "$0")/.." && pwd)"
UNMINED="${UNMINED:-$HOME/.local/lib/unmined/unmined-cli}"
PY="${PYBIN:-$REPO/.venv/bin/python3}"      # needs Pillow
OUT="$REPO/web/static/map"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT

bash "$REPO/scripts/world-backup.sh" "$TMP/world.tgz" >/dev/null
mkdir -p "$TMP/w" "$TMP/render" && tar -xzf "$TMP/world.tgz" -C "$TMP/w"
"$UNMINED" web render --world="$TMP/w/claude_build" --output="$TMP/render" \
  --zoomin 2 --zoomout 4 --shadows 3d --imageformat png --background "#ff00ff" --centerx 20 --centerz 8 -c \
  > "$TMP/render.log" 2>&1 || { tail -20 "$TMP/render.log"; exit 1; }
grep -q "0 Chunks failed" "$TMP/render.log" || { grep -E "Chunks|ERR|WRN" "$TMP/render.log" | tail -5; }

"$PY" - "$TMP/render" <<'EOF'
import glob, os, re, sys
import numpy as np
from PIL import Image
root = sys.argv[1]; T = os.path.join(root, "tiles")
GRASS = np.array([111, 145, 68, 255], dtype=np.uint8)
def path(z, x, y, ext): return os.path.join(T, f"zoom.{z}", str(x // 10), str(y // 10), f"tile.{x}.{y}.{ext}")
levels = sorted(int(d.split(".", 1)[1]) for d in os.listdir(T) if d.startswith("zoom."))
top, bottom = levels[-1], levels[0]
# 1. the full-detail level: repaint "no stored terrain" (black, or background magenta with 3d shadows) as lawn
tiles = {}
for f in glob.glob(os.path.join(T, f"zoom.{top}", "**", "*.png"), recursive=True):
    x, y = map(int, re.match(r"tile\.(-?\d+)\.(-?\d+)\.png$", os.path.basename(f)).groups())
    a = np.array(Image.open(f).convert("RGBA")); rgb = a[..., :3].astype(np.int16)
    a[(rgb.max(axis=2) < 8) | ((rgb[..., 0] > 200) & (rgb[..., 1] < 60) & (rgb[..., 2] > 200)) | (a[..., 3] == 0)] = GRASS
    tiles[(x, y)] = Image.fromarray(a, "RGBA").convert("RGB")
# 2. rebuild every lower level from the repainted one (uNmINeD's own were averaged before the repaint: pink fringes)
for d in levels[:-1]:
    for f in glob.glob(os.path.join(T, f"zoom.{d}", "**", "*.png"), recursive=True): os.remove(f)
grass = Image.new("RGB", (256, 256), tuple(int(v) for v in GRASS[:3]))
out = {top: tiles}
for z in range(top - 1, bottom - 1, -1):
    up, cur = out[z + 1], {}
    for (x, y) in {(cx // 2, cy // 2) for (cx, cy) in up}:
        canvas = Image.new("RGB", (512, 512))
        for dx in (0, 1):
            for dy in (0, 1): canvas.paste(up.get((2 * x + dx, 2 * y + dy), grass), (256 * dx, 256 * dy))
        cur[(x, y)] = canvas.resize((256, 256), Image.Resampling.BOX)
    out[z] = cur
n = 0
for z, ts in out.items():
    for (x, y), im in ts.items():
        p = path(z, x, y, "webp"); os.makedirs(os.path.dirname(p), exist_ok=True)
        im.save(p, "WEBP", quality=85, method=4); n += 1
for f in glob.glob(os.path.join(T, f"zoom.{top}", "**", "*.png"), recursive=True): os.remove(f)
p = os.path.join(root, "unmined.map.properties.js")
s = open(p).read()
s = re.sub(r'imageFormat: "png"', 'imageFormat: "webp"', s)
s = re.sub(r'showGrid: true', 'showGrid: false', s)
s = re.sub(r'background: "[^"]*"', 'background: ""', s)
open(p, "w").write(s)
print(f"{n} tiles, levels {bottom}..{top}")
EOF

# live player markers (admins only; web/static/live-players.js polls /rest/server_players)
sed -i 's#</body>#    <script src="../live-players.js"></script>\n</body>#' "$TMP/render/index.html"
grep -q 'live-players.js' "$TMP/render/index.html" || { echo "could not inject live-players.js"; exit 1; }

# the viewer's page background beyond the rendered area: lawn too
printf '\nhtml, body, #map, .ol-viewport { background: #6f9144 !important; }\n' >> "$TMP/render/index.css"

# swap in atomically: the site never serves a half-written map
rm -rf "$OUT.new" && cp -a "$TMP/render" "$OUT.new" && date -u +%FT%TZ > "$OUT.new/rendered_at.txt"
rm -rf "$OUT.old"; [ -d "$OUT" ] && mv "$OUT" "$OUT.old"; mv "$OUT.new" "$OUT"; rm -rf "$OUT.old"
echo "map: $(grep -oE '[0-9]+ Chunks rendered' "$TMP/render.log"), $(du -sh "$OUT" | cut -f1) at $OUT"
