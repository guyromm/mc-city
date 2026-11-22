-- Name: server_players; Type: VIEW; Schema: api; Owner: -
--

CREATE OR REPLACE VIEW api.server_players AS
 SELECT (p.value ->> 'name'::text) AS name,
    (p.value -> 'pos'::text) AS pos,
    (p.value ->> 'dim'::text) AS dim
   FROM minecraft.server_status s,
    LATERAL jsonb_array_elements(s.players) p(value)
  WHERE minecraft.is_admin();


--
