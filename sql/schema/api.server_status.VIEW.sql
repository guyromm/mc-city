-- Name: server_status; Type: VIEW; Schema: api; Owner: -
--

CREATE OR REPLACE VIEW api.server_status AS
 SELECT online,
    version,
    jsonb_array_length(players) AS players_online,
    max_players,
    plots_built,
    checked_at,
    online_since
   FROM minecraft.server_status;


--
