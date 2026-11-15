-- Name: admins id; Type: DEFAULT; Schema: minecraft; Owner: -
--

ALTER TABLE ONLY minecraft.admins ALTER COLUMN id SET DEFAULT nextval('minecraft.admins_id_seq'::regclass);


--
