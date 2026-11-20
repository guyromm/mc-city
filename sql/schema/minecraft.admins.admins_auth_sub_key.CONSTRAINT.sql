-- Name: admins admins_auth_sub_key; Type: CONSTRAINT; Schema: minecraft; Owner: -
--

ALTER TABLE ONLY minecraft.admins
    ADD CONSTRAINT admins_auth_sub_key UNIQUE (auth_sub);


--
