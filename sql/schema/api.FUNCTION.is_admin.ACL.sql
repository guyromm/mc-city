-- Name: FUNCTION is_admin(); Type: ACL; Schema: api; Owner: -
--

REVOKE ALL ON FUNCTION api.is_admin() FROM PUBLIC;
GRANT ALL ON FUNCTION api.is_admin() TO minecraft_anon;
GRANT ALL ON FUNCTION api.is_admin() TO minecraft_web;


--
