-- Name: set_password(text, text); Type: FUNCTION; Schema: api; Owner: -
--

CREATE OR REPLACE FUNCTION api.set_password(p_token text, p_password text) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'minecraft', 'public'
    AS $$
DECLARE a minecraft.admins; fails int;
BEGIN
  SELECT count(*) INTO fails FROM minecraft.login_attempts WHERE email = '(setup)' AND NOT ok AND at > now() - interval '15 minutes';
  IF fails >= 10 THEN RETURN jsonb_build_object('error', 'too many attempts, wait 15 minutes'); END IF;
  IF length(coalesce(p_password, '')) < 10 THEN RETURN jsonb_build_object('error', 'use at least 10 characters'); END IF;
  SELECT * INTO a FROM minecraft.admins
   WHERE setup_hash = encode(digest(coalesce(p_token, ''), 'sha256'), 'hex') AND setup_until > now() AND enabled;
  IF a.id IS NULL THEN
    INSERT INTO minecraft.login_attempts(email, ok) VALUES ('(setup)', false);
    RETURN jsonb_build_object('error', 'this setup link is invalid or has expired');
  END IF;
  UPDATE minecraft.admins SET pass_hash = crypt(p_password, gen_salt('bf', 10)), setup_hash = NULL, setup_until = NULL
   WHERE id = a.id RETURNING * INTO a;
  INSERT INTO minecraft.login_attempts(email, ok) VALUES (a.email, true);
  RETURN minecraft.issue_session(a);
END $$;


--
