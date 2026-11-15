-- Name: login_attempts id; Type: DEFAULT; Schema: minecraft; Owner: -
--

ALTER TABLE ONLY minecraft.login_attempts ALTER COLUMN id SET DEFAULT nextval('minecraft.login_attempts_id_seq'::regclass);


--
