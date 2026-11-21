-- Name: is_admin(); Type: FUNCTION; Schema: minecraft; Owner: -
--

CREATE OR REPLACE FUNCTION minecraft.is_admin() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'minecraft', 'public'
    AS $$
  SELECT coalesce(c->>'iss' = 'https://auth.webgma.co.il' AND c->>'aud' = 'minecraft' AND c->>'role' = 'minecraft_admin', false)
  FROM minecraft.jwt_claims() c $$;


--
