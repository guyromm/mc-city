-- auth.webgma.co.il SSO (#275/13, doc:auth-integration §3/§5). PostgREST has already verified the signature (own HS256 or
-- auth's RS256, jwt-aud=minecraft). An auth token counts as admin only if iss = auth, aud = minecraft, role = minecraft_web
-- (the role auth grants us) AND its sub is the auth user id recorded on an enabled admin (guy's, set by hand).
-- Our own tokens (no iss) keep working exactly as before.
BEGIN;
ALTER TABLE minecraft.admins ADD COLUMN IF NOT EXISTS auth_sub text UNIQUE;
COMMENT ON COLUMN minecraft.admins.auth_sub IS 'auth.webgma.co.il user id (JWT sub) allowed to sign in as this admin through SSO';
CREATE OR REPLACE FUNCTION minecraft.is_admin() RETURNS boolean
  LANGUAGE sql STABLE SECURITY DEFINER SET search_path TO 'minecraft', 'public' AS $$
  SELECT coalesce((SELECT a.enabled FROM minecraft.admins a
                    WHERE a.id = nullif(minecraft.jwt_claims()->>'admin_id', '')::int
                      AND minecraft.jwt_claims()->>'iss' IS NULL
                      AND minecraft.jwt_claims()->>'role' = 'minecraft_web'), false)
      OR coalesce((SELECT a.enabled FROM minecraft.admins a, minecraft.jwt_claims() c
                    WHERE c->>'iss' = 'https://auth.webgma.co.il' AND c->>'aud' = 'minecraft'
                      AND c->>'role' = 'minecraft_web' AND a.auth_sub IS NOT NULL AND a.auth_sub = c->>'sub'), false) $$;
COMMIT;
