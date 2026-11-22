-- Name: server_status; Type: TABLE; Schema: minecraft; Owner: -
--

CREATE TABLE minecraft.server_status (
    id boolean DEFAULT true NOT NULL,
    online boolean DEFAULT false NOT NULL,
    version text,
    players jsonb DEFAULT '[]'::jsonb NOT NULL,
    max_players integer,
    plots_built integer,
    tour jsonb,
    checked_at timestamp with time zone DEFAULT now() NOT NULL,
    online_since timestamp with time zone,
    CONSTRAINT server_status_id_check CHECK (id)
);


--
