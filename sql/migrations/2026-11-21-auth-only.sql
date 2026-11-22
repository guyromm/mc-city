-- auth.webgma.co.il replaces the local login (#275/13 DONE CHECKLIST, board #3346/#3348, guy 11-20).
-- Admin = a token from auth for this system with the granted role: iss + aud + role, no sub list. Who holds the grant is
-- auth's business (its grants table). The local email/password login, its setup tokens, its JWT signing and its secret go.
BEGIN;
CREATE OR REPLACE FUNCTION minecraft.is_admin() RETURNS boolean
  LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO 'minecraft', 'public' AS $$
  SELECT coalesce(c->>'iss' = 'https://auth.webgma.co.il' AND c->>'aud' = 'minecraft' AND c->>'role' = 'minecraft_web', false)
  FROM minecraft.jwt_claims() c $$;
DROP FUNCTION api.login(text, text);
DROP FUNCTION api.set_password(text, text);
DROP FUNCTION minecraft.admin_setup_token(text, interval);
DROP FUNCTION minecraft.issue_session(minecraft.admins);
DROP FUNCTION minecraft.jwt_sign(jsonb);
DROP TABLE minecraft.login_attempts;
DROP TABLE minecraft.admins;
DROP TABLE minecraft.secrets;
COMMIT;
