-- Name: is_admin(); Type: FUNCTION; Schema: api; Owner: -
--

CREATE OR REPLACE FUNCTION api.is_admin() RETURNS boolean
    LANGUAGE sql STABLE
    AS $$ SELECT minecraft.is_admin() $$;


--
