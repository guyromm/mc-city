-- Name: login(text, text); Type: FUNCTION; Schema: api; Owner: -
--

CREATE OR REPLACE FUNCTION api.login(p_email text, p_password text) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'minecraft', 'public'
    AS $$
DECLARE a minecraft.admins; fails int;
BEGIN
  SELECT count(*) INTO fails FROM minecraft.login_attempts
   WHERE lower(email) = lower(p_email) AND NOT ok AND at > now() - interval '15 minutes';
  IF fails >= 10 THEN RETURN jsonb_build_object('error', 'too many attempts, wait 15 minutes'); END IF;
  SELECT * INTO a FROM minecraft.admins WHERE lower(email) = lower(trim(p_email)) AND enabled;
  IF a.id IS NULL OR a.pass_hash IS NULL OR a.pass_hash <> crypt(p_password, a.pass_hash) THEN
    INSERT INTO minecraft.login_attempts(email, ok) VALUES (left(p_email, 200), false);
    RETURN jsonb_build_object('error', 'invalid email or password');   -- no RAISE: it would roll back the attempt row
  END IF;
  INSERT INTO minecraft.login_attempts(email, ok) VALUES (a.email, true);
  RETURN minecraft.issue_session(a);
END $$;


--
