-- Self-inspection 11-24 (#65 item 10): extension functions in public (pgcrypto, pgjwt, pg_stat_statements; owned by
-- postgres, so their EXECUTE can't be revoked here) are EXECUTE-able by PUBLIC. Nothing of ours uses them and PostgREST
-- exposes only `api`; still, take USAGE on schema public away from everyone but the owner, so anon/web/admin can call 0 of
-- them. Also drop the template1 leftovers granting other projects' roles (telegram CREATE, tweet_reader USAGE) on it.
REVOKE USAGE ON SCHEMA public FROM PUBLIC;
REVOKE CREATE ON SCHEMA public FROM telegram;
REVOKE USAGE ON SCHEMA public FROM tweet_reader;
GRANT USAGE ON SCHEMA public TO minecraft;
