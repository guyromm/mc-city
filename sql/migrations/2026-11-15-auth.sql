-- minecraft: admin auth for the web UI (/login, /claude). Pattern from miko/crosspost: api.login -> HS256 JWT
-- (role minecraft_web), signed with the secret kept as DATA in minecraft.secrets (synced from .env by sql/apply.sh).
-- Gate for every admin object: minecraft.is_admin(). Admins set their own password through a one-time setup token.
BEGIN;
CREATE SCHEMA IF NOT EXISTS minecraft;

CREATE TABLE minecraft.secrets (k text PRIMARY KEY, v text NOT NULL);
REVOKE ALL ON minecraft.secrets FROM PUBLIC;

CREATE TABLE minecraft.admins (
  id          serial PRIMARY KEY,
  email       text NOT NULL UNIQUE,
  name        text,
  pass_hash   text,                       -- NULL until set through a setup token
  enabled     boolean NOT NULL DEFAULT true,
  setup_hash  text,                       -- sha256 of a one-time setup token (the token itself is never stored)
  setup_until timestamptz,
  created_at  timestamptz NOT NULL DEFAULT now(),
  last_login  timestamptz
);
COMMENT ON COLUMN minecraft.admins.setup_hash IS 'sha256 hex of a one-time token from minecraft.admin_setup_token(); cleared on use';

CREATE TABLE minecraft.login_attempts (
  id    bigserial PRIMARY KEY,
  email text NOT NULL,
  ok    boolean NOT NULL,
  at    timestamptz NOT NULL DEFAULT now()
);

CREATE FUNCTION minecraft.jwt_claims() RETURNS jsonb LANGUAGE sql STABLE AS $$
  SELECT coalesce(nullif(current_setting('request.jwt.claims', true), ''), '{}')::jsonb $$;

CREATE FUNCTION minecraft.jwt_sign(payload jsonb) RETURNS text
  LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path TO minecraft, public AS $$
DECLARE secret text;
BEGIN
  SELECT v INTO secret FROM minecraft.secrets WHERE k = 'jwt_secret';
  IF secret IS NULL OR secret = '' THEN RAISE EXCEPTION 'jwt secret not configured'; END IF;
  RETURN public.sign(payload::json, secret, 'HS256');
END $$;
REVOKE ALL ON FUNCTION minecraft.jwt_sign(jsonb) FROM PUBLIC;

CREATE FUNCTION minecraft.is_admin() RETURNS boolean
  LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO minecraft, public AS $$
  SELECT coalesce((SELECT a.enabled FROM minecraft.admins a
                    WHERE a.id = nullif(minecraft.jwt_claims()->>'admin_id', '')::int
                      AND minecraft.jwt_claims()->>'role' = 'minecraft_web'), false) $$;

-- issue (or re-issue) a one-time setup token for an admin; run by the owner in psql, never exposed through the API
CREATE FUNCTION minecraft.admin_setup_token(p_email text, p_valid interval DEFAULT '48 hours') RETURNS text
  LANGUAGE plpgsql SET search_path TO minecraft, public AS $$
DECLARE t text := encode(gen_random_bytes(24), 'hex');
BEGIN
  UPDATE minecraft.admins SET setup_hash = encode(digest(t, 'sha256'), 'hex'), setup_until = now() + p_valid
   WHERE lower(email) = lower(p_email);
  IF NOT FOUND THEN RAISE EXCEPTION 'no admin %', p_email; END IF;
  RETURN t;
END $$;
REVOKE ALL ON FUNCTION minecraft.admin_setup_token(text, interval) FROM PUBLIC;

CREATE FUNCTION minecraft.issue_session(a minecraft.admins) RETURNS jsonb
  LANGUAGE plpgsql SECURITY DEFINER SET search_path TO minecraft, public AS $$
DECLARE exp bigint := extract(epoch FROM now() + interval '30 days')::bigint;
BEGIN
  UPDATE minecraft.admins SET last_login = now() WHERE id = a.id;
  RETURN jsonb_build_object('token', minecraft.jwt_sign(jsonb_build_object('role', 'minecraft_web', 'admin_id', a.id,
           'email', a.email, 'name', coalesce(a.name, a.email), 'admin', true, 'exp', exp)),
         'email', a.email, 'name', a.name, 'exp', exp);
END $$;
REVOKE ALL ON FUNCTION minecraft.issue_session(minecraft.admins) FROM PUBLIC;

CREATE FUNCTION api.login(p_email text, p_password text) RETURNS jsonb
  LANGUAGE plpgsql SECURITY DEFINER SET search_path TO minecraft, public AS $$
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

-- set the password with a one-time setup token, and sign in
CREATE FUNCTION api.set_password(p_token text, p_password text) RETURNS jsonb
  LANGUAGE plpgsql SECURITY DEFINER SET search_path TO minecraft, public AS $$
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

CREATE FUNCTION api.is_admin() RETURNS boolean LANGUAGE sql STABLE AS $$ SELECT minecraft.is_admin() $$;

GRANT USAGE ON SCHEMA minecraft TO minecraft_anon, minecraft_web;
GRANT EXECUTE ON FUNCTION minecraft.is_admin(), minecraft.jwt_claims() TO minecraft_anon, minecraft_web;
REVOKE ALL ON FUNCTION api.login(text, text), api.set_password(text, text), api.is_admin() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION api.login(text, text), api.set_password(text, text), api.is_admin() TO minecraft_anon, minecraft_web;
COMMIT;
