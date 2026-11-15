-- Name: admins; Type: TABLE; Schema: minecraft; Owner: -
--

CREATE TABLE minecraft.admins (
    id integer NOT NULL,
    email text NOT NULL,
    name text,
    pass_hash text,
    enabled boolean DEFAULT true NOT NULL,
    setup_hash text,
    setup_until timestamp with time zone,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    last_login timestamp with time zone
);


--
