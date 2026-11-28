-- board #5130 (ofana #5126): claude-ui's api views gate reads with is_admin() but were auto-updatable without CHECK OPTION,
-- so a role with INSERT/UPDATE on them could write past the admin check. Here only the owner (minecraft) has write grants,
-- and no PostgREST role is or inherits it: not exposed. Fixed anyway (upstream claude-ui review 527).
ALTER VIEW api.claude_msg    SET (check_option = local);
ALTER VIEW api.claude_file   SET (check_option = local);
ALTER VIEW api.claude_img    SET (check_option = local);
ALTER VIEW api.claude_status SET (check_option = local);
