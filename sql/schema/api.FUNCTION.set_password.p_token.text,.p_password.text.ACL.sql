-- Name: FUNCTION set_password(p_token text, p_password text); Type: ACL; Schema: api; Owner: -
--

REVOKE ALL ON FUNCTION api.set_password(p_token text, p_password text) FROM PUBLIC;
GRANT ALL ON FUNCTION api.set_password(p_token text, p_password text) TO minecraft_anon;
GRANT ALL ON FUNCTION api.set_password(p_token text, p_password text) TO minecraft_web;


--
