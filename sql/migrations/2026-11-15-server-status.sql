-- minecraft: live server status for the web UI, written every ~30 s by the `status` worker (src/status_worker.py).
-- Public: online / version / player count / city size. Admins only: who is online and where.
BEGIN;
CREATE TABLE minecraft.server_status (
  id          boolean PRIMARY KEY DEFAULT true CHECK (id),   -- singleton row
  online      boolean NOT NULL DEFAULT false,
  version     text,
  players     jsonb NOT NULL DEFAULT '[]',                    -- [{name,pos,dim}] from the pack's `players` op
  max_players int,
  plots_built int,
  tour        jsonb,
  checked_at  timestamptz NOT NULL DEFAULT now(),
  online_since timestamptz
);
INSERT INTO minecraft.server_status(id) VALUES (true);

CREATE VIEW api.server_status AS
  SELECT online, version, jsonb_array_length(players) AS players_online, max_players, plots_built, checked_at, online_since
    FROM minecraft.server_status;
CREATE VIEW api.server_players AS
  SELECT p->>'name' AS name, p->'pos' AS pos, p->>'dim' AS dim
    FROM minecraft.server_status s, jsonb_array_elements(s.players) p
   WHERE minecraft.is_admin();
GRANT SELECT ON api.server_status TO minecraft_anon, minecraft_web;
GRANT SELECT ON api.server_players TO minecraft_web;
COMMIT;
