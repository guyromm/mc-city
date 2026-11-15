-- Name: issue_session(minecraft.admins); Type: FUNCTION; Schema: minecraft; Owner: -
--

CREATE OR REPLACE FUNCTION minecraft.issue_session(a minecraft.admins) RETURNS jsonb
    LANGUAGE plpgsql SECURITY DEFINER
    SET search_path TO 'minecraft', 'public'
    AS $$
DECLARE exp bigint := extract(epoch FROM now() + interval '30 days')::bigint;
BEGIN
  UPDATE minecraft.admins SET last_login = now() WHERE id = a.id;
  RETURN jsonb_build_object('token', minecraft.jwt_sign(jsonb_build_object('role', 'minecraft_web', 'admin_id', a.id,
           'email', a.email, 'name', coalesce(a.name, a.email), 'admin', true, 'exp', exp)),
         'email', a.email, 'name', a.name, 'exp', exp);
END $$;


--
