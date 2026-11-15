-- Name: login_attempts; Type: TABLE; Schema: minecraft; Owner: -
--

CREATE TABLE minecraft.login_attempts (
    id bigint NOT NULL,
    email text NOT NULL,
    ok boolean NOT NULL,
    at timestamp with time zone DEFAULT now() NOT NULL
);


--
