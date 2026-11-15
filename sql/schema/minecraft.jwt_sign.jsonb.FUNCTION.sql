-- Name: jwt_sign(jsonb); Type: FUNCTION; Schema: minecraft; Owner: -
--

CREATE OR REPLACE FUNCTION minecraft.jwt_sign(payload jsonb) RETURNS text
    LANGUAGE plpgsql STABLE SECURITY DEFINER
    SET search_path TO 'minecraft', 'public'
    AS $$
DECLARE secret text;
BEGIN
  SELECT v INTO secret FROM minecraft.secrets WHERE k = 'jwt_secret';
  IF secret IS NULL OR secret = '' THEN RAISE EXCEPTION 'jwt secret not configured'; END IF;
  RETURN public.sign(payload::json, secret, 'HS256');
END $$;


--
