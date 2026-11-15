-- Name: admin_setup_token(text, interval); Type: FUNCTION; Schema: minecraft; Owner: -
--

CREATE OR REPLACE FUNCTION minecraft.admin_setup_token(p_email text, p_valid interval DEFAULT '48:00:00'::interval) RETURNS text
    LANGUAGE plpgsql
    SET search_path TO 'minecraft', 'public'
    AS $$
DECLARE t text := encode(gen_random_bytes(24), 'hex');
BEGIN
  UPDATE minecraft.admins SET setup_hash = encode(digest(t, 'sha256'), 'hex'), setup_until = now() + p_valid
   WHERE lower(email) = lower(p_email);
  IF NOT FOUND THEN RAISE EXCEPTION 'no admin %', p_email; END IF;
  RETURN t;
END $$;


--
