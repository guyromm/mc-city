-- Name: is_admin(); Type: FUNCTION; Schema: minecraft; Owner: -
--

CREATE OR REPLACE FUNCTION minecraft.is_admin() RETURNS boolean
    LANGUAGE sql STABLE SECURITY DEFINER
    SET search_path TO 'minecraft', 'public'
    AS $$
  SELECT coalesce((SELECT a.enabled FROM minecraft.admins a
                    WHERE a.id = nullif(minecraft.jwt_claims()->>'admin_id', '')::int
                      AND minecraft.jwt_claims()->>'role' = 'minecraft_web'), false) $$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
