-- Name: FUNCTION login(p_email text, p_password text); Type: ACL; Schema: api; Owner: -
--

REVOKE ALL ON FUNCTION api.login(p_email text, p_password text) FROM PUBLIC;
GRANT ALL ON FUNCTION api.login(p_email text, p_password text) TO minecraft_anon;
GRANT ALL ON FUNCTION api.login(p_email text, p_password text) TO minecraft_web;


--
