-- Name: jwt_claims(); Type: FUNCTION; Schema: minecraft; Owner: -
--

CREATE OR REPLACE FUNCTION minecraft.jwt_claims() RETURNS jsonb
    LANGUAGE sql STABLE
    AS $$
  SELECT coalesce(nullif(current_setting('request.jwt.claims', true), ''), '{}')::jsonb $$;


--
