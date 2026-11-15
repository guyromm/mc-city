-- Name: admins admins_email_key; Type: CONSTRAINT; Schema: minecraft; Owner: -
--

ALTER TABLE ONLY minecraft.admins
    ADD CONSTRAINT admins_email_key UNIQUE (email);


--
