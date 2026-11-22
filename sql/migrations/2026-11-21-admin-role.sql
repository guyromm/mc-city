-- auth #3359: the general web role must not be admin by itself. Admin = auth's grant of minecraft_admin (a DB role created
-- by resource-manager, member of minecraft_authenticator); it inherits minecraft_web's rights.
BEGIN;
GRANT minecraft_web TO minecraft_admin;
CREATE OR REPLACE FUNCTION minecraft.is_admin() RETURNS boolean
  LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO 'minecraft', 'public' AS $$
  SELECT coalesce(c->>'iss' = 'https://auth.webgma.co.il' AND c->>'aud' = 'minecraft' AND c->>'role' = 'minecraft_admin', false)
  FROM minecraft.jwt_claims() c $$;
COMMIT;
