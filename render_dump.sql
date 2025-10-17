--
-- PostgreSQL database dump
--

\restrict CD56chOgyAGmkI4qmwJLK6hm7qAEYsgw6c4giCkMaKC4YZhAI3AMX6RxgxKOaso

-- Dumped from database version 17.6 (Debian 17.6-1.pgdg12+1)
-- Dumped by pg_dump version 17.6

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

-- *not* creating schema, since initdb creates it


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: alembic_version; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.alembic_version (
    version_num character varying(32) NOT NULL
);


--
-- Name: attachment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.attachment (
    id integer NOT NULL,
    task_id integer NOT NULL,
    filename character varying(255) NOT NULL,
    unique_filename character varying(255) NOT NULL,
    storage_path character varying(500) NOT NULL,
    mimetype character varying(100),
    filesize integer,
    uploaded_by_user_id integer NOT NULL,
    upload_timestamp timestamp without time zone NOT NULL
);


--
-- Name: attachment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.attachment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: attachment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.attachment_id_seq OWNED BY public.attachment.id;


--
-- Name: category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.category (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(200),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.category_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.category_id_seq OWNED BY public.category.id;


--
-- Name: change_log_entry; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.change_log_entry (
    id integer NOT NULL,
    user_id integer NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    action character varying(50) NOT NULL,
    record_type character varying(50) NOT NULL,
    record_id integer,
    old_data json,
    new_data json,
    description text
);


--
-- Name: change_log_entry_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.change_log_entry_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: change_log_entry_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.change_log_entry_id_seq OWNED BY public.change_log_entry.id;


--
-- Name: comment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.comment (
    id integer NOT NULL,
    content text NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    task_id integer NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: comment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.comment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: comment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.comment_id_seq OWNED BY public.comment.id;


--
-- Name: event; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event (
    id integer NOT NULL,
    title character varying(100) NOT NULL,
    description text,
    due_date timestamp without time zone NOT NULL,
    end_date timestamp without time zone,
    location character varying(100),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    author_id integer NOT NULL,
    category_id integer,
    status_id integer,
    is_published boolean DEFAULT false NOT NULL,
    is_cancelled boolean DEFAULT false NOT NULL
);


--
-- Name: event_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_id_seq OWNED BY public.event.id;


--
-- Name: event_permission; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.event_permission (
    id integer NOT NULL,
    event_id integer NOT NULL,
    user_id integer NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: event_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.event_permission_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: event_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.event_permission_id_seq OWNED BY public.event_permission.id;


--
-- Name: group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."group" (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(200),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: group_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.group_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.group_id_seq OWNED BY public."group".id;


--
-- Name: notification; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.notification (
    id integer NOT NULL,
    user_id integer NOT NULL,
    message text NOT NULL,
    link_url character varying(500),
    is_read boolean NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    related_object_type character varying(50),
    related_object_id integer
);


--
-- Name: notification_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.notification_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: notification_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.notification_id_seq OWNED BY public.notification.id;


--
-- Name: password_reset_token; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_reset_token (
    id integer NOT NULL,
    token_uuid character varying(36) NOT NULL,
    user_id integer NOT NULL,
    expiration_date timestamp without time zone NOT NULL,
    is_used boolean NOT NULL,
    created_at timestamp without time zone NOT NULL
);


--
-- Name: password_reset_token_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.password_reset_token_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: password_reset_token_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.password_reset_token_id_seq OWNED BY public.password_reset_token.id;


--
-- Name: push_subscription; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.push_subscription (
    id integer NOT NULL,
    user_id integer NOT NULL,
    endpoint character varying(512) NOT NULL,
    p256dh character varying(255) NOT NULL,
    auth character varying(255) NOT NULL,
    "timestamp" timestamp without time zone
);


--
-- Name: push_subscription_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.push_subscription_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: push_subscription_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.push_subscription_id_seq OWNED BY public.push_subscription.id;


--
-- Name: role; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.role (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(200),
    can_view_event boolean NOT NULL,
    can_edit_event boolean NOT NULL,
    can_manage_permissions boolean NOT NULL,
    can_create_event boolean NOT NULL,
    can_create_task boolean NOT NULL,
    can_edit_task boolean NOT NULL,
    can_delete_task boolean NOT NULL,
    can_complete_task boolean NOT NULL,
    can_uncomplete_task boolean NOT NULL,
    can_upload_task_audio boolean NOT NULL,
    can_delete_task_audio boolean NOT NULL,
    can_view_task_history boolean NOT NULL,
    can_manage_task_comments boolean NOT NULL,
    can_upload_attachments boolean NOT NULL,
    can_manage_attachments boolean NOT NULL,
    can_publish_event boolean DEFAULT false NOT NULL,
    can_cancel_event boolean DEFAULT false NOT NULL,
    can_duplicate_event boolean DEFAULT false NOT NULL,
    can_view_event_registrations boolean DEFAULT false NOT NULL,
    can_view_event_reports boolean DEFAULT false NOT NULL
);


--
-- Name: role_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.role_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: role_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.role_id_seq OWNED BY public.role.id;


--
-- Name: status; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.status (
    id integer NOT NULL,
    name character varying(80) NOT NULL,
    type character varying(20) NOT NULL,
    description character varying(255)
);


--
-- Name: status_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.status_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: status_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.status_id_seq OWNED BY public.status.id;


--
-- Name: task; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task (
    id integer NOT NULL,
    title character varying(100) NOT NULL,
    description text,
    notes text,
    due_date timestamp without time zone NOT NULL,
    original_due_date timestamp without time zone,
    cloud_storage_link character varying(500),
    link_notes text,
    audio_path character varying(500),
    audio_duration_seconds integer,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    event_id integer NOT NULL,
    task_status_id integer NOT NULL,
    task_category_id integer,
    is_completed boolean NOT NULL,
    completed_at timestamp without time zone,
    completed_by_id integer
);


--
-- Name: task_assignment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_assignment (
    task_id integer NOT NULL,
    user_id integer NOT NULL,
    assigned_at timestamp without time zone NOT NULL
);


--
-- Name: task_category; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_category (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(200),
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: task_category_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.task_category_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: task_category_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.task_category_id_seq OWNED BY public.task_category.id;


--
-- Name: task_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.task_history (
    id integer NOT NULL,
    task_id integer NOT NULL,
    action_type character varying(50) NOT NULL,
    description text,
    old_value text,
    new_value text,
    user_id integer NOT NULL,
    "timestamp" timestamp without time zone NOT NULL,
    comment text
);


--
-- Name: task_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.task_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: task_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.task_history_id_seq OWNED BY public.task_history.id;


--
-- Name: task_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.task_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: task_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.task_id_seq OWNED BY public.task.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."user" (
    id integer NOT NULL,
    username character varying(20) NOT NULL,
    email character varying(120) NOT NULL,
    password_hash character varying(200),
    role_id integer NOT NULL,
    image_file character varying(20) NOT NULL,
    is_active_db boolean NOT NULL,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL
);


--
-- Name: user_group; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_group (
    user_id integer NOT NULL,
    group_id integer NOT NULL,
    assigned_at timestamp without time zone NOT NULL
);


--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: attachment id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attachment ALTER COLUMN id SET DEFAULT nextval('public.attachment_id_seq'::regclass);


--
-- Name: category id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.category ALTER COLUMN id SET DEFAULT nextval('public.category_id_seq'::regclass);


--
-- Name: change_log_entry id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_log_entry ALTER COLUMN id SET DEFAULT nextval('public.change_log_entry_id_seq'::regclass);


--
-- Name: comment id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comment ALTER COLUMN id SET DEFAULT nextval('public.comment_id_seq'::regclass);


--
-- Name: event id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event ALTER COLUMN id SET DEFAULT nextval('public.event_id_seq'::regclass);


--
-- Name: event_permission id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_permission ALTER COLUMN id SET DEFAULT nextval('public.event_permission_id_seq'::regclass);


--
-- Name: group id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."group" ALTER COLUMN id SET DEFAULT nextval('public.group_id_seq'::regclass);


--
-- Name: notification id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification ALTER COLUMN id SET DEFAULT nextval('public.notification_id_seq'::regclass);


--
-- Name: password_reset_token id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_token ALTER COLUMN id SET DEFAULT nextval('public.password_reset_token_id_seq'::regclass);


--
-- Name: push_subscription id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.push_subscription ALTER COLUMN id SET DEFAULT nextval('public.push_subscription_id_seq'::regclass);


--
-- Name: role id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role ALTER COLUMN id SET DEFAULT nextval('public.role_id_seq'::regclass);


--
-- Name: status id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status ALTER COLUMN id SET DEFAULT nextval('public.status_id_seq'::regclass);


--
-- Name: task id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task ALTER COLUMN id SET DEFAULT nextval('public.task_id_seq'::regclass);


--
-- Name: task_category id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_category ALTER COLUMN id SET DEFAULT nextval('public.task_category_id_seq'::regclass);


--
-- Name: task_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_history ALTER COLUMN id SET DEFAULT nextval('public.task_history_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.alembic_version (version_num) FROM stdin;
d905d3821ce6
\.


--
-- Data for Name: attachment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.attachment (id, task_id, filename, unique_filename, storage_path, mimetype, filesize, uploaded_by_user_id, upload_timestamp) FROM stdin;
\.


--
-- Data for Name: category; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.category (id, name, description, created_at, updated_at) FROM stdin;
1	Regional	Região Centro-Sul do estado de Mato Grosso  |  COMADEMAT	2025-09-24 00:25:33.842718	2025-09-24 00:25:33.842725
2	Local	Campo de Cuiabá e Região	2025-09-24 00:26:00.288897	2025-09-24 00:26:00.2889
3	Estadual	Região do estado de Mato Grosso	2025-09-24 00:26:25.304745	2025-09-24 00:26:25.304748
\.


--
-- Data for Name: change_log_entry; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.change_log_entry (id, user_id, "timestamp", action, record_type, record_id, old_data, new_data, description) FROM stdin;
1	1	2025-09-24 00:41:46.798986	create	Event	1	\N	{"id": 1, "title": "Batismo", "description": "", "due_date": "2025-09-28T09:00:00", "end_date": "2025-09-28T12:00:00", "location": "Grande Templo", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:41:46.773390", "updated_at": "2025-09-24T00:41:46.773394"}	Evento 'Batismo' criado.
2	1	2025-09-24 00:43:23.327805	create	Task	1	\N	{"id": 1, "title": "Contratar Fot\\u00f3grafos", "description": "", "notes": "", "due_date": "2025-09-24T20:00:00", "original_due_date": "2025-09-24T20:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 1, "task_status_id": 4, "task_status_name": "Em Andamento", "task_category_id": 5, "task_category_name": "Conte\\u00fado", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T00:43:23.274482", "updated_at": "2025-09-24T00:43:23.274485", "attachments_count": 0}	Tarefa 'Contratar Fotógrafos' criada no evento 'Batismo'.
3	1	2025-09-24 00:48:13.12234	create	Event	2	\N	{"id": 2, "title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)", "description": "", "due_date": "2025-09-29T08:30:00", "end_date": "2025-09-29T12:01:00", "location": "Audit\\u00f3rio A1", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:48:13.099891", "updated_at": "2025-09-24T00:48:13.099895"}	Evento 'Reunião Ministerial dos Setores de Cuiabá e Região 8h30 (A1)' criado.
4	1	2025-09-24 00:49:28.058937	create	Event	3	\N	{"id": 3, "title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)", "description": "", "due_date": "2025-10-27T08:30:00", "end_date": "2025-10-27T08:30:00", "location": "Audit\\u00f3rio A1", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:49:27.957798", "updated_at": "2025-09-24T00:49:27.957801"}	Evento 'Reunião Ministerial dos Setores de Cuiabá e Região 8h30 (A1)' criado.
5	1	2025-09-24 00:50:29.046284	create	Event	4	\N	{"id": 4, "title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)", "description": "", "due_date": "2025-11-24T08:30:00", "end_date": "2025-11-24T08:30:00", "location": "Audit\\u00f3rio A1", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:50:29.035299", "updated_at": "2025-09-24T00:50:29.035302"}	Evento 'Reunião Ministerial dos Setores de Cuiabá e Região 8h30 (A1)' criado.
6	1	2025-09-24 00:51:18.661092	create	Event	5	\N	{"id": 5, "title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)", "description": "", "due_date": "2025-12-29T08:30:00", "end_date": "2025-12-29T12:00:00", "location": "Audit\\u00f3rio A1", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:51:18.650557", "updated_at": "2025-09-24T00:51:18.650560"}	Evento 'Reunião Ministerial dos Setores de Cuiabá e Região 8h30 (A1)' criado.
7	1	2025-09-24 00:52:41.198834	create	Event	6	\N	{"id": 6, "title": "Reuni\\u00e3o de Obreiros - Cuiab\\u00e1 e Regi\\u00e3o - 08h30 (N)", "description": "", "due_date": "2025-10-11T08:30:00", "end_date": "2025-10-11T12:00:00", "location": "Nave - Grande Templo", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:52:41.186919", "updated_at": "2025-09-24T00:52:41.186923"}	Evento 'Reunião de Obreiros - Cuiabá e Região - 08h30 (N)' criado.
8	1	2025-09-24 00:53:34.090528	create	Event	7	\N	{"id": 7, "title": "Reuni\\u00e3o de Obreiros - Cuiab\\u00e1 e Regi\\u00e3o - 08h30 (N)", "description": "", "due_date": "2025-11-08T08:30:00", "end_date": "2025-11-08T08:30:00", "location": "Nave - Grande Templo", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:53:34.075777", "updated_at": "2025-09-24T00:53:34.075780"}	Evento 'Reunião de Obreiros - Cuiabá e Região - 08h30 (N)' criado.
9	1	2025-09-24 00:53:34.177406	create	Event	8	\N	{"id": 8, "title": "Reuni\\u00e3o de Obreiros - Cuiab\\u00e1 e Regi\\u00e3o - 08h30 (N)", "description": "", "due_date": "2025-11-08T08:30:00", "end_date": "2025-11-08T08:30:00", "location": "Nave - Grande Templo", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:53:34.161343", "updated_at": "2025-09-24T00:53:34.161346"}	Evento 'Reunião de Obreiros - Cuiabá e Região - 08h30 (N)' criado.
10	1	2025-09-24 00:54:09.493501	create	Event	9	\N	{"id": 9, "title": "Reuni\\u00e3o de Obreiros - Cuiab\\u00e1 e Regi\\u00e3o - 08h30 (N)", "description": "", "due_date": "2025-12-13T08:30:00", "end_date": "2025-12-13T12:00:00", "location": "Nave - Grande Templo", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:54:09.482586", "updated_at": "2025-09-24T00:54:09.482589"}	Evento 'Reunião de Obreiros - Cuiabá e Região - 08h30 (N)' criado.
11	1	2025-09-24 00:56:17.279397	create	Event	10	\N	{"id": 10, "title": "83\\u00aa AGO/COMADEMAT 19h", "description": "", "due_date": "2025-11-04T19:00:00", "end_date": "2025-11-07T12:00:00", "location": "Nave - Grande Templo", "author_id": 1, "category_id": 3, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:56:17.269211", "updated_at": "2025-09-24T00:56:17.269214"}	Evento '83ª AGO/COMADEMAT 19h' criado.
12	1	2025-09-24 01:02:28.346045	update	Task	1	{"id": 1, "title": "Contratar Fot\\u00f3grafos", "description": "", "notes": "", "due_date": "2025-09-24T20:00:00", "original_due_date": "2025-09-24T20:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 1, "task_status_id": 4, "task_status_name": "Em Andamento", "task_category_id": 5, "task_category_name": "Conte\\u00fado", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T00:43:23.274482", "updated_at": "2025-09-24T00:43:23.274485", "attachments_count": 0}	{"id": 1, "title": "Contratar Fot\\u00f3grafos", "description": "", "notes": "", "due_date": "2025-09-24T20:00:00", "original_due_date": "2025-09-24T20:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 1, "task_status_id": 4, "task_status_name": "Em Andamento", "task_category_id": 5, "task_category_name": "Conte\\u00fado", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T00:43:23.274482", "updated_at": "2025-09-24T00:43:23.274485", "attachments_count": 0}	Tarefa 'Contratar Fotógrafos' atualizada no evento 'Batismo'.
40	2	2025-09-27 12:20:54.390881	create	Comment	8	\N	{"id": 8, "content": "Pastor Jaime, os fot\\u00f3grafos j\\u00e1 est\\u00e3o convocados.\\nComo criei um grupo no whats pra alinhamento, j\\u00e1 havia feito a convoca\\u00e7\\u00e3o e alinhamento por l\\u00e1.\\n\\nSer\\u00e3o Ellen, Jane e Donato", "timestamp": "2025-09-27T12:20:54.382500", "task_id": 2, "user_id": 2, "username": "jorair"}	Comentário adicionado por 'jorair' na tarefa 'Registro Fotográfico'.
13	1	2025-09-24 01:02:28.398401	update	Task	1	{"id": 1, "title": "Contratar Fot\\u00f3grafos", "description": "", "notes": "", "due_date": "2025-09-24T20:00:00", "original_due_date": "2025-09-24T20:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 1, "task_status_id": 4, "task_status_name": "Em Andamento", "task_category_id": 5, "task_category_name": "Conte\\u00fado", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T00:43:23.274482", "updated_at": "2025-09-24T00:43:23.274485", "attachments_count": 0}	{"id": 1, "title": "Contratar Fot\\u00f3grafos", "description": "", "notes": "", "due_date": "2025-09-24T20:00:00", "original_due_date": "2025-09-24T20:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 1, "task_status_id": 4, "task_status_name": "Em Andamento", "task_category_id": 5, "task_category_name": "Conte\\u00fado", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T00:43:23.274482", "updated_at": "2025-09-24T00:43:23.274485", "attachments_count": 0}	Tarefa 'Contratar Fotógrafos' atualizada no evento 'Batismo'.
14	1	2025-09-24 01:05:13.858242	create	Attachment	1	\N	{"id": 1, "task_id": 1, "filename": "DSC_4177.JPG", "unique_filename": "2d619e8d-2077-495b-8a63-6cdc5b6aac07.jpg", "storage_path": "/opt/render/project/src/instance/uploads/attachments/2d619e8d-2077-495b-8a63-6cdc5b6aac07.jpg", "mimetype": "image/jpeg", "filesize": 0, "uploaded_by_user_id": 1, "uploaded_by_username": "admin", "upload_timestamp": "2025-09-24T01:05:13.845683", "download_url": "/attachment/1/download"}	Anexo 'DSC_4177.JPG' adicionado à tarefa 'Contratar Fotógrafos' por admin.
15	1	2025-09-24 01:05:37.408197	create	Attachment	2	\N	{"id": 2, "task_id": 1, "filename": "DSC_4177.JPG", "unique_filename": "1a8a1eca-6597-4e09-a01b-3b72512a377c.jpg", "storage_path": "/opt/render/project/src/instance/uploads/attachments/1a8a1eca-6597-4e09-a01b-3b72512a377c.jpg", "mimetype": "image/jpeg", "filesize": 0, "uploaded_by_user_id": 1, "uploaded_by_username": "admin", "upload_timestamp": "2025-09-24T01:05:37.398513", "download_url": "/attachment/2/download"}	Anexo 'DSC_4177.JPG' adicionado à tarefa 'Contratar Fotógrafos' por admin.
16	1	2025-09-24 03:58:34.977056	delete	Attachment	2	{"id": 2, "task_id": 1, "filename": "DSC_4177.JPG", "unique_filename": "1a8a1eca-6597-4e09-a01b-3b72512a377c.jpg", "storage_path": "/opt/render/project/src/instance/uploads/attachments/1a8a1eca-6597-4e09-a01b-3b72512a377c.jpg", "mimetype": "image/jpeg", "filesize": 0, "uploaded_by_user_id": 1, "uploaded_by_username": "admin", "upload_timestamp": "2025-09-24T01:05:37.398513", "download_url": "/attachment/2/download"}	\N	Anexo 'DSC_4177.JPG' excluído da tarefa 'Contratar Fotógrafos' por admin.
17	1	2025-09-24 03:58:37.259999	delete	Attachment	1	{"id": 1, "task_id": 1, "filename": "DSC_4177.JPG", "unique_filename": "2d619e8d-2077-495b-8a63-6cdc5b6aac07.jpg", "storage_path": "/opt/render/project/src/instance/uploads/attachments/2d619e8d-2077-495b-8a63-6cdc5b6aac07.jpg", "mimetype": "image/jpeg", "filesize": 0, "uploaded_by_user_id": 1, "uploaded_by_username": "admin", "upload_timestamp": "2025-09-24T01:05:13.845683", "download_url": "/attachment/1/download"}	\N	Anexo 'DSC_4177.JPG' excluído da tarefa 'Contratar Fotógrafos' por admin.
18	5	2025-09-24 19:13:52.177798	update	Task	1	{"id": 1, "title": "Contratar Fot\\u00f3grafos", "description": "", "notes": "", "due_date": "2025-09-24T20:00:00", "original_due_date": "2025-09-24T20:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 1, "task_status_id": 4, "task_status_name": "Em Andamento", "task_category_id": 5, "task_category_name": "Conte\\u00fado", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T00:43:23.274482", "updated_at": "2025-09-24T00:43:23.274485", "attachments_count": 0}	{"id": 1, "title": "Contratar Fot\\u00f3grafos", "description": "", "notes": "", "due_date": "2025-09-24T20:00:00", "original_due_date": "2025-09-24T20:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "b647201a-231f-48f0-85c6-60a243a64d10.webm", "audio_duration_seconds": 3, "event_id": 1, "task_status_id": 4, "task_status_name": "Em Andamento", "task_category_id": 5, "task_category_name": "Conte\\u00fado", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T00:43:23.274482", "updated_at": "2025-09-24T19:13:52.159568", "attachments_count": 0}	Áudio adicionado/atualizado na tarefa 'Contratar Fotógrafos'. Duração: 3s.
19	5	2025-09-24 19:14:27.859148	create	Attachment	3	\N	{"id": 3, "task_id": 1, "filename": "tempFileForShare_20250916-182710.jpg", "unique_filename": "ba09ec00-6c6a-4c5f-bd46-e06c659401f6.jpg", "storage_path": "/opt/render/project/src/instance/uploads/attachments/ba09ec00-6c6a-4c5f-bd46-e06c659401f6.jpg", "mimetype": "image/jpeg", "filesize": 481396, "uploaded_by_user_id": 5, "uploaded_by_username": "jaime", "upload_timestamp": "2025-09-24T19:14:27.825230", "download_url": "/attachment/3/download"}	Anexo 'tempFileForShare_20250916-182710.jpg' adicionado à tarefa 'Contratar Fotógrafos' por jaime.
20	5	2025-09-24 19:15:03.325178	create	Comment	1	\N	{"id": 1, "content": "Tudo bem", "timestamp": "2025-09-24T19:15:03.315043", "task_id": 1, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Contratar Fotógrafos'.
21	5	2025-09-24 19:15:03.378626	create	Comment	2	\N	{"id": 2, "content": "Tudo bem", "timestamp": "2025-09-24T19:15:03.372517", "task_id": 1, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Contratar Fotógrafos'.
22	1	2025-09-24 19:19:27.357716	delete	Attachment	3	{"id": 3, "task_id": 1, "filename": "tempFileForShare_20250916-182710.jpg", "unique_filename": "ba09ec00-6c6a-4c5f-bd46-e06c659401f6.jpg", "storage_path": "/opt/render/project/src/instance/uploads/attachments/ba09ec00-6c6a-4c5f-bd46-e06c659401f6.jpg", "mimetype": "image/jpeg", "filesize": 481396, "uploaded_by_user_id": 5, "uploaded_by_username": "jaime", "upload_timestamp": "2025-09-24T19:14:27.825230", "download_url": "/attachment/3/download"}	\N	Anexo 'tempFileForShare_20250916-182710.jpg' excluído da tarefa 'Contratar Fotógrafos' por admin.
41	5	2025-09-27 23:54:27.613666	create	Comment	9	\N	{"id": 9, "content": "@julia @felipe", "timestamp": "2025-09-27T23:54:27.587967", "task_id": 5, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Edição Conteúdo '.
42	5	2025-09-27 23:54:50.709372	create	Comment	10	\N	{"id": 10, "content": "@luis.estiano como est\\u00e1 para amanh\\u00e3?", "timestamp": "2025-09-27T23:54:50.693378", "task_id": 5, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Edição Conteúdo '.
23	1	2025-09-24 19:19:45.094326	update	Task	1	{"id": 1, "title": "Contratar Fot\\u00f3grafos", "description": "", "notes": "", "due_date": "2025-09-24T20:00:00", "original_due_date": "2025-09-24T20:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "b647201a-231f-48f0-85c6-60a243a64d10.webm", "audio_duration_seconds": 3, "event_id": 1, "task_status_id": 4, "task_status_name": "Em Andamento", "task_category_id": 5, "task_category_name": "Conte\\u00fado", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T00:43:23.274482", "updated_at": "2025-09-24T19:13:52.159568", "attachments_count": 0}	{"id": 1, "title": "Contratar Fot\\u00f3grafos", "description": "", "notes": "", "due_date": "2025-09-24T20:00:00", "original_due_date": "2025-09-24T20:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 1, "task_status_id": 4, "task_status_name": "Em Andamento", "task_category_id": 5, "task_category_name": "Conte\\u00fado", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T00:43:23.274482", "updated_at": "2025-09-24T19:19:45.085803", "attachments_count": 0}	Áudio excluído da tarefa 'Contratar Fotógrafos'.
24	2	2025-09-24 20:14:05.757066	create	Event	11	\N	{"id": 11, "title": "Batismo", "description": "", "due_date": "2025-09-28T10:00:00", "end_date": "2025-09-28T12:00:00", "location": "Grande Templo", "author_id": 2, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T20:14:05.739913", "updated_at": "2025-09-24T20:14:05.739918"}	Evento 'Batismo' criado.
25	2	2025-09-24 20:15:16.630135	create	Task	2	\N	{"id": 2, "title": "Registro Fotogr\\u00e1fico", "description": "", "notes": "", "due_date": "2025-09-28T13:00:00", "original_due_date": "2025-09-28T13:00:00", "cloud_storage_link": "https://drive.google.com/drive/folders/1XB6I3JcD4ZJ6XQFB_20ZFc5Dylh_8cA7?usp=sharing", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 11, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 1, "task_category_name": "Redes Sociais", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T20:15:16.604000", "updated_at": "2025-09-24T20:15:16.604004", "attachments_count": 0}	Tarefa 'Registro Fotográfico' criada no evento 'Batismo'.
26	5	2025-09-24 21:20:11.780715	delete	Event	1	{"id": 1, "title": "Batismo", "description": "", "due_date": "2025-09-28T09:00:00", "end_date": "2025-09-28T12:00:00", "location": "Grande Templo", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:41:46.773390", "updated_at": "2025-09-24T00:41:46.773394"}	\N	Evento 'Batismo' deletado.
27	5	2025-09-24 21:23:54.52056	create	Task	3	\N	{"id": 3, "title": "Registro Imagens", "description": "Verificar quais conte\\u00fados ser\\u00e3o criados ", "notes": "", "due_date": "2025-09-25T12:00:00", "original_due_date": "2025-09-25T12:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 2, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": null, "task_category_name": null, "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T21:23:54.500719", "updated_at": "2025-09-24T21:23:54.500722", "attachments_count": 0}	Tarefa 'Registro Imagens' criada no evento 'Reunião Ministerial dos Setores de Cuiabá e Região 8h30 (A1)'.
28	1	2025-09-25 02:38:23.175633	update	Task	2	{"id": 2, "title": "Registro Fotogr\\u00e1fico", "description": "", "notes": "", "due_date": "2025-09-28T13:00:00", "original_due_date": "2025-09-28T13:00:00", "cloud_storage_link": "https://drive.google.com/drive/folders/1XB6I3JcD4ZJ6XQFB_20ZFc5Dylh_8cA7?usp=sharing", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 11, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 1, "task_category_name": "Redes Sociais", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T20:15:16.604000", "updated_at": "2025-09-24T20:15:16.604004", "attachments_count": 0}	{"id": 2, "title": "Registro Fotogr\\u00e1fico", "description": "", "notes": "", "due_date": "2025-09-28T13:00:00", "original_due_date": "2025-09-28T13:00:00", "cloud_storage_link": "https://drive.google.com/drive/folders/1XB6I3JcD4ZJ6XQFB_20ZFc5Dylh_8cA7?usp=sharing", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 11, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 1, "task_category_name": "Redes Sociais", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T20:15:16.604000", "updated_at": "2025-09-24T20:15:16.604004", "attachments_count": 0}	Tarefa 'Registro Fotográfico' atualizada no evento 'Batismo'.
29	1	2025-09-25 02:38:45.285749	create	Comment	3	\N	{"id": 3, "content": "Confirmar fot\\u00f3grafos", "timestamp": "2025-09-25T02:38:45.277992", "task_id": 2, "user_id": 1, "username": "admin"}	Comentário adicionado por 'admin' na tarefa 'Registro Fotográfico'.
30	2	2025-09-25 02:57:50.138842	update	Task	2	{"id": 2, "title": "Registro Fotogr\\u00e1fico", "description": "", "notes": "", "due_date": "2025-09-28T13:00:00", "original_due_date": "2025-09-28T13:00:00", "cloud_storage_link": "https://drive.google.com/drive/folders/1XB6I3JcD4ZJ6XQFB_20ZFc5Dylh_8cA7?usp=sharing", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 11, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 1, "task_category_name": "Redes Sociais", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T20:15:16.604000", "updated_at": "2025-09-24T20:15:16.604004", "attachments_count": 0}	{"id": 2, "title": "Registro Fotogr\\u00e1fico", "description": "", "notes": "", "due_date": "2025-09-28T13:00:00", "original_due_date": "2025-09-28T13:00:00", "cloud_storage_link": "https://drive.google.com/drive/folders/1XB6I3JcD4ZJ6XQFB_20ZFc5Dylh_8cA7?usp=sharing", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 11, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 1, "task_category_name": "Redes Sociais", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T20:15:16.604000", "updated_at": "2025-09-24T20:15:16.604004", "attachments_count": 0}	Tarefa 'Registro Fotográfico' atualizada no evento 'Batismo'.
31	2	2025-09-25 14:10:26.942198	update	Task	2	{"id": 2, "title": "Registro Fotogr\\u00e1fico", "description": "", "notes": "", "due_date": "2025-09-28T13:00:00", "original_due_date": "2025-09-28T13:00:00", "cloud_storage_link": "https://drive.google.com/drive/folders/1XB6I3JcD4ZJ6XQFB_20ZFc5Dylh_8cA7?usp=sharing", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 11, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 1, "task_category_name": "Redes Sociais", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T20:15:16.604000", "updated_at": "2025-09-24T20:15:16.604004", "attachments_count": 0}	{"id": 2, "title": "Registro Fotogr\\u00e1fico", "description": "", "notes": "", "due_date": "2025-09-28T13:00:00", "original_due_date": "2025-09-28T13:00:00", "cloud_storage_link": "https://drive.google.com/drive/folders/1XB6I3JcD4ZJ6XQFB_20ZFc5Dylh_8cA7?usp=sharing", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 11, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 1, "task_category_name": "Redes Sociais", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T20:15:16.604000", "updated_at": "2025-09-24T20:15:16.604004", "attachments_count": 0}	Tarefa 'Registro Fotográfico' atualizada no evento 'Batismo'.
32	2	2025-09-25 14:11:22.226437	create	Task	4	\N	{"id": 4, "title": "Cobertura", "description": "", "notes": "", "due_date": "2025-12-26T10:08:00", "original_due_date": "2025-12-26T10:08:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 5, "task_status_id": 6, "task_status_name": "Concluido", "task_category_id": 5, "task_category_name": "Conte\\u00fado", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-25T14:11:22.209790", "updated_at": "2025-09-25T14:11:22.209793", "attachments_count": 0}	Tarefa 'Cobertura' criada no evento 'Reunião Ministerial dos Setores de Cuiabá e Região 8h30 (A1)'.
33	5	2025-09-25 22:05:44.220833	update	Task	3	{"id": 3, "title": "Registro Imagens", "description": "Verificar quais conte\\u00fados ser\\u00e3o criados ", "notes": "", "due_date": "2025-09-25T12:00:00", "original_due_date": "2025-09-25T12:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 2, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": null, "task_category_name": null, "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T21:23:54.500719", "updated_at": "2025-09-24T21:23:54.500722", "attachments_count": 0}	{"id": 3, "title": "Registro Imagens", "description": "Verificar quais conte\\u00fados ser\\u00e3o criados ", "notes": "", "due_date": "2025-09-25T12:00:00", "original_due_date": "2025-09-25T12:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 2, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": null, "task_category_name": null, "assigned_user_ids": [null, null], "assigned_usernames": ["jorair", "jorair"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T21:23:54.500719", "updated_at": "2025-09-24T21:23:54.500722", "attachments_count": 0}	Tarefa 'Registro Imagens' atualizada no evento 'Reunião Ministerial dos Setores de Cuiabá e Região 8h30 (A1)'.
34	5	2025-09-25 22:06:22.208203	update	Task	3	{"id": 3, "title": "Registro Imagens", "description": "Verificar quais conte\\u00fados ser\\u00e3o criados ", "notes": "", "due_date": "2025-09-25T12:00:00", "original_due_date": "2025-09-25T12:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 2, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": null, "task_category_name": null, "assigned_user_ids": [2], "assigned_usernames": ["jorair"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T21:23:54.500719", "updated_at": "2025-09-24T21:23:54.500722", "attachments_count": 0}	{"id": 3, "title": "Registro Imagens", "description": "Verificar quais conte\\u00fados ser\\u00e3o criados ", "notes": "", "due_date": "2025-09-25T12:00:00", "original_due_date": "2025-09-25T12:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 2, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": null, "task_category_name": null, "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T21:23:54.500719", "updated_at": "2025-09-24T21:23:54.500722", "attachments_count": 0}	Tarefa 'Registro Imagens' atualizada no evento 'Reunião Ministerial dos Setores de Cuiabá e Região 8h30 (A1)'.
35	5	2025-09-25 22:38:37.566533	create	Comment	4	\N	{"id": 4, "content": "Jorair, os coment\\u00e1rios aqui s\\u00e3o guardados e enviados para o email. Depois irei melhorar a l\\u00f3gica e implementar o @men\\u00e7\\u00e3o assim as mensagem seguem somente quando houver men\\u00e7\\u00e3o da pessoa.", "timestamp": "2025-09-25T22:38:37.398830", "task_id": 2, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Registro Fotográfico'.
36	5	2025-09-25 22:40:08.850037	create	Comment	5	\N	{"id": 5, "content": "Assim que ler essa mensagem, retorne aqui, por gentileza..", "timestamp": "2025-09-25T22:40:08.713127", "task_id": 2, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Registro Fotográfico'.
37	5	2025-09-25 22:50:32.519981	create	Task	5	\N	{"id": 5, "title": "Edi\\u00e7\\u00e3o Conte\\u00fado ", "description": "J\\u00falia, verificar as capas para os posts", "notes": "", "due_date": "2025-09-27T13:00:00", "original_due_date": "2025-09-27T13:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 11, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [12], "assigned_usernames": ["julia"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-25T22:50:32.513119", "updated_at": "2025-09-25T22:50:32.513121", "attachments_count": 0}	Tarefa 'Edição Conteúdo ' criada no evento 'Batismo'.
38	3	2025-09-26 15:27:28.711151	create	Comment	6	\N	{"id": 6, "content": "Pastor o @jorair ja confirmou com o donato a cobertura fotografica", "timestamp": "2025-09-26T15:27:28.571899", "task_id": 2, "user_id": 3, "username": "felipe"}	Comentário adicionado por 'felipe' na tarefa 'Registro Fotográfico'.
39	3	2025-09-26 15:27:58.450287	create	Comment	7	\N	{"id": 7, "content": "@Julia chegou de verificar mais pessoas para escala ?", "timestamp": "2025-09-26T15:27:58.192435", "task_id": 5, "user_id": 3, "username": "felipe"}	Comentário adicionado por 'felipe' na tarefa 'Edição Conteúdo '.
43	5	2025-09-27 23:56:18.962553	update	Task	5	{"id": 5, "title": "Edi\\u00e7\\u00e3o Conte\\u00fado ", "description": "J\\u00falia, verificar as capas para os posts", "notes": "", "due_date": "2025-09-27T13:00:00", "original_due_date": "2025-09-27T13:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 11, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [12], "assigned_usernames": ["julia"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-25T22:50:32.513119", "updated_at": "2025-09-25T22:50:32.513121", "attachments_count": 0}	{"id": 5, "title": "Edi\\u00e7\\u00e3o Conte\\u00fado ", "description": "J\\u00falia, verificar as capas para os posts", "notes": "", "due_date": "2025-09-27T13:00:00", "original_due_date": "2025-09-27T13:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 11, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [null, null, null, null], "assigned_usernames": ["julia", "julia", "felipe", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-25T22:50:32.513119", "updated_at": "2025-09-25T22:50:32.513121", "attachments_count": 0}	Tarefa 'Edição Conteúdo ' atualizada no evento 'Batismo'.
44	5	2025-09-28 00:01:56.750306	create	Comment	11	\N	{"id": 11, "content": "@jorair est\\u00e1 funcionando agora a men\\u00e7\\u00e3o  \\"@name_do_usuario\\"", "timestamp": "2025-09-28T00:01:56.735010", "task_id": 2, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Registro Fotográfico'.
51	5	2025-09-29 17:36:08.062506	create	Comment	18	\N	{"id": 18, "content": "@felipe tudo certo com a cobertura?", "timestamp": "2025-09-29T17:36:07.949205", "task_id": 5, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Edição Conteúdo '.
52	5	2025-09-29 18:33:12.969943	create	Comment	19	\N	{"id": 19, "content": "@felipe tudo certo ent\\u00e3o?", "timestamp": "2025-09-29T18:33:12.961915", "task_id": 5, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Edição Conteúdo '.
53	5	2025-09-29 18:34:25.324095	create	Comment	20	\N	{"id": 20, "content": "@admin teste", "timestamp": "2025-09-29T18:34:25.316383", "task_id": 5, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Edição Conteúdo '.
54	5	2025-09-29 18:36:34.755914	create	Comment	21	\N	{"id": 21, "content": "@admin teste", "timestamp": "2025-09-29T18:36:34.747910", "task_id": 3, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Registro Imagens'.
55	5	2025-09-29 18:36:34.791857	create	Comment	22	\N	{"id": 22, "content": "@admin teste", "timestamp": "2025-09-29T18:36:34.783527", "task_id": 3, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Registro Imagens'.
56	5	2025-09-29 18:37:56.895678	create	Comment	23	\N	{"id": 23, "content": "@admin", "timestamp": "2025-09-29T18:37:56.888791", "task_id": 2, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Registro Fotográfico'.
57	5	2025-09-29 22:33:01.4421	create	Comment	24	\N	{"id": 24, "content": "@admin esta ok", "timestamp": "2025-09-29T22:33:01.411173", "task_id": 2, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Registro Fotográfico'.
58	5	2025-09-29 22:35:21.555657	create	Comment	25	\N	{"id": 25, "content": "@julia finalizar", "timestamp": "2025-09-29T22:35:21.543134", "task_id": 5, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Edição Conteúdo '.
59	5	2025-09-29 23:45:03.753227	update	Event	11	{"id": 11, "title": "Batismo", "description": "", "due_date": "2025-09-28T10:00:00", "end_date": "2025-09-28T12:00:00", "location": "Grande Templo", "author_id": 2, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T20:14:05.739913", "updated_at": "2025-09-24T20:14:05.739918", "is_published": false, "is_cancelled": false}	{"id": 11, "title": "Batismo", "description": "", "due_date": "2025-09-28T10:00:00", "end_date": "2025-09-28T12:00:00", "location": "Grande Templo", "author_id": 2, "category_id": 2, "status_id": 3, "status_name": "Arquivado", "created_at": "2025-09-24T20:14:05.739913", "updated_at": "2025-09-29T23:45:03.728677", "is_published": false, "is_cancelled": false}	Evento 'Batismo' atualizado.
67	5	2025-10-06 22:33:12.415433	update	Event	12	{"id": 12, "title": "INAUGURA\\u00c7\\u00c3O TEMPLO BELVEDERE ", "description": "", "due_date": "2025-11-09T09:00:00", "end_date": "2025-11-09T12:00:00", "location": "R. Martim Pescador - Res. Maria de Lourdes, Cuiab\\u00e1 - MT", "author_id": 5, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-10-06T22:32:39.118571", "updated_at": "2025-10-06T22:33:10.263854", "is_published": false, "is_cancelled": false}	{"id": 12, "title": "INAUGURA\\u00c7\\u00c3O TEMPLO BELVEDERE ", "description": "", "due_date": "2025-11-09T09:00:00", "end_date": "2025-11-09T12:00:00", "location": "R. Martim Pescador - Res. Maria de Lourdes, Cuiab\\u00e1 - MT", "author_id": 5, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-10-06T22:32:39.118571", "updated_at": "2025-10-06T22:33:12.407056", "is_published": true, "is_cancelled": false}	Evento 'INAUGURAÇÃO TEMPLO BELVEDERE ' publicado.
60	2	2025-09-30 19:18:23.735167	update	Task	2	{"id": 2, "title": "Registro Fotogr\\u00e1fico", "description": "", "notes": "", "due_date": "2025-09-28T13:00:00", "original_due_date": "2025-09-28T13:00:00", "cloud_storage_link": "https://drive.google.com/drive/folders/1XB6I3JcD4ZJ6XQFB_20ZFc5Dylh_8cA7?usp=sharing", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 11, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 1, "task_category_name": "Redes Sociais", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-09-24T20:15:16.604000", "updated_at": "2025-09-24T20:15:16.604004", "attachments_count": 0}	{"id": 2, "title": "Registro Fotogr\\u00e1fico", "description": "", "notes": "", "due_date": "2025-09-28T13:00:00", "original_due_date": "2025-09-28T13:00:00", "cloud_storage_link": "https://drive.google.com/drive/folders/1XB6I3JcD4ZJ6XQFB_20ZFc5Dylh_8cA7?usp=sharing", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 11, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 1, "task_category_name": "Redes Sociais", "assigned_user_ids": [], "assigned_usernames": [], "is_completed": true, "completed_at": "2025-09-30T19:18:23.720860", "completed_by_id": 2, "completed_by_username": "jorair", "created_at": "2025-09-24T20:15:16.604000", "updated_at": "2025-09-30T19:18:23.722730", "attachments_count": 0}	Tarefa 'Registro Fotográfico' concluída por jorair. Comentário: 'fotos no Drive'
61	5	2025-10-02 00:04:37.585063	update	Event	2	{"id": 2, "title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)", "description": "", "due_date": "2025-09-29T08:30:00", "end_date": "2025-09-29T12:01:00", "location": "Audit\\u00f3rio A1", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:48:13.099891", "updated_at": "2025-09-24T00:48:13.099895", "is_published": false, "is_cancelled": false}	{"id": 2, "title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)", "description": "", "due_date": "2025-09-29T08:30:00", "end_date": "2025-09-29T12:01:00", "location": "Audit\\u00f3rio A1", "author_id": 1, "category_id": 2, "status_id": 3, "status_name": "Arquivado", "created_at": "2025-09-24T00:48:13.099891", "updated_at": "2025-10-02T00:04:37.577940", "is_published": false, "is_cancelled": false}	Evento 'Reunião Ministerial dos Setores de Cuiabá e Região 8h30 (A1)' atualizado.
62	5	2025-10-06 22:27:26.371492	update	Event	6	{"id": 6, "title": "Reuni\\u00e3o de Obreiros - Cuiab\\u00e1 e Regi\\u00e3o - 08h30 (N)", "description": "", "due_date": "2025-10-11T08:30:00", "end_date": "2025-10-11T12:00:00", "location": "Nave - Grande Templo", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:52:41.186919", "updated_at": "2025-09-24T00:52:41.186923", "is_published": false, "is_cancelled": false}	{"id": 6, "title": "Reuni\\u00e3o de Obreiros - Cuiab\\u00e1 e Regi\\u00e3o - 08h30 (N)", "description": "", "due_date": "2025-10-11T08:30:00", "end_date": "2025-10-11T12:00:00", "location": "Nave - Grande Templo", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:52:41.186919", "updated_at": "2025-10-06T22:27:26.358006", "is_published": true, "is_cancelled": false}	Evento 'Reunião de Obreiros - Cuiabá e Região - 08h30 (N)' publicado.
63	5	2025-10-06 22:27:34.232434	update	Event	2	{"id": 2, "title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)", "description": "", "due_date": "2025-09-29T08:30:00", "end_date": "2025-09-29T12:01:00", "location": "Audit\\u00f3rio A1", "author_id": 1, "category_id": 2, "status_id": 3, "status_name": "Arquivado", "created_at": "2025-09-24T00:48:13.099891", "updated_at": "2025-10-02T00:04:37.577940", "is_published": false, "is_cancelled": false}	{"id": 2, "title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)", "description": "", "due_date": "2025-09-29T08:30:00", "end_date": "2025-09-29T12:01:00", "location": "Audit\\u00f3rio A1", "author_id": 1, "category_id": 2, "status_id": 3, "status_name": "Arquivado", "created_at": "2025-09-24T00:48:13.099891", "updated_at": "2025-10-06T22:27:34.226004", "is_published": true, "is_cancelled": false}	Evento 'Reunião Ministerial dos Setores de Cuiabá e Região 8h30 (A1)' publicado.
64	5	2025-10-06 22:28:21.349675	update	Event	3	{"id": 3, "title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)", "description": "", "due_date": "2025-10-27T08:30:00", "end_date": "2025-10-27T08:30:00", "location": "Audit\\u00f3rio A1", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:49:27.957798", "updated_at": "2025-09-24T00:49:27.957801", "is_published": false, "is_cancelled": false}	{"id": 3, "title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)", "description": "", "due_date": "2025-10-27T08:30:00", "end_date": "2025-10-27T08:30:00", "location": "Audit\\u00f3rio A1", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:49:27.957798", "updated_at": "2025-10-06T22:28:21.344333", "is_published": true, "is_cancelled": false}	Evento 'Reunião Ministerial dos Setores de Cuiabá e Região 8h30 (A1)' publicado.
65	5	2025-10-06 22:32:39.127647	create	Event	12	\N	{"id": 12, "title": "INAGURA\\u00c7\\u00c3O TEMPLO BELVEDERE ", "description": "", "due_date": "2025-11-09T09:00:00", "end_date": "2025-11-09T12:00:00", "location": "R. Martim Pescador - Res. Maria de Lourdes, Cuiab\\u00e1 - MT", "author_id": 5, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-10-06T22:32:39.118571", "updated_at": "2025-10-06T22:32:39.119519", "is_published": false, "is_cancelled": false}	Evento 'INAGURAÇÃO TEMPLO BELVEDERE ' criado.
66	5	2025-10-06 22:33:10.269622	update	Event	12	{"id": 12, "title": "INAGURA\\u00c7\\u00c3O TEMPLO BELVEDERE ", "description": "", "due_date": "2025-11-09T09:00:00", "end_date": "2025-11-09T12:00:00", "location": "R. Martim Pescador - Res. Maria de Lourdes, Cuiab\\u00e1 - MT", "author_id": 5, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-10-06T22:32:39.118571", "updated_at": "2025-10-06T22:32:39.119519", "is_published": false, "is_cancelled": false}	{"id": 12, "title": "INAUGURA\\u00c7\\u00c3O TEMPLO BELVEDERE ", "description": "", "due_date": "2025-11-09T09:00:00", "end_date": "2025-11-09T12:00:00", "location": "R. Martim Pescador - Res. Maria de Lourdes, Cuiab\\u00e1 - MT", "author_id": 5, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-10-06T22:32:39.118571", "updated_at": "2025-10-06T22:33:10.263854", "is_published": false, "is_cancelled": false}	Evento 'INAUGURAÇÃO TEMPLO BELVEDERE ' atualizado.
68	5	2025-10-06 22:40:22.199085	create	Task	6	\N	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [3], "assigned_usernames": ["felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T22:40:22.186846", "attachments_count": 0}	Tarefa 'Preparativos para o Evento' criada no evento 'INAUGURAÇÃO TEMPLO BELVEDERE '.
69	5	2025-10-06 22:41:53.446609	update	Task	6	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [3], "assigned_usernames": ["felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T22:40:22.186846", "attachments_count": 0}	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "cdc4574f-5e11-45b8-8af2-91747a54733f.webm", "audio_duration_seconds": 31, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [3], "assigned_usernames": ["felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T22:41:53.428850", "attachments_count": 0}	Áudio adicionado/atualizado na tarefa 'Preparativos para o Evento'. Duração: 31s.
70	5	2025-10-06 22:43:10.618384	update	Task	6	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "cdc4574f-5e11-45b8-8af2-91747a54733f.webm", "audio_duration_seconds": 31, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [3], "assigned_usernames": ["felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T22:41:53.428850", "attachments_count": 0}	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "cdc4574f-5e11-45b8-8af2-91747a54733f.webm", "audio_duration_seconds": 31, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [3], "assigned_usernames": ["felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T22:41:53.428850", "attachments_count": 0}	Tarefa 'Preparativos para o Evento' atualizada no evento 'INAUGURAÇÃO TEMPLO BELVEDERE '.
71	5	2025-10-06 22:46:04.651009	create	Task	7	\N	{"id": 7, "title": "Escala da Equipe para o Evento", "description": "", "notes": "", "due_date": "2025-10-10T12:00:00", "original_due_date": "2025-10-10T12:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 5, "task_category_name": "Conte\\u00fado", "assigned_user_ids": [12, null, null], "assigned_usernames": ["julia", "luis.estiano", "luis.estiano"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:46:04.643012", "updated_at": "2025-10-06T22:46:04.643016", "attachments_count": 0}	Tarefa 'Escala da Equipe para o Evento' criada no evento 'INAUGURAÇÃO TEMPLO BELVEDERE '.
72	5	2025-10-06 22:46:44.172381	update	Task	7	{"id": 7, "title": "Escala da Equipe para o Evento", "description": "", "notes": "", "due_date": "2025-10-10T12:00:00", "original_due_date": "2025-10-10T12:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": null, "audio_duration_seconds": null, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 5, "task_category_name": "Conte\\u00fado", "assigned_user_ids": [12, 19], "assigned_usernames": ["julia", "luis.estiano"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:46:04.643012", "updated_at": "2025-10-06T22:46:04.643016", "attachments_count": 0}	{"id": 7, "title": "Escala da Equipe para o Evento", "description": "", "notes": "", "due_date": "2025-10-10T12:00:00", "original_due_date": "2025-10-10T12:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "df2ae5af-e637-4476-87e8-fbeddf33ed2a.webm", "audio_duration_seconds": 24, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 5, "task_category_name": "Conte\\u00fado", "assigned_user_ids": [12, 19], "assigned_usernames": ["julia", "luis.estiano"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:46:04.643012", "updated_at": "2025-10-06T22:46:44.159443", "attachments_count": 0}	Áudio adicionado/atualizado na tarefa 'Escala da Equipe para o Evento'. Duração: 24s.
73	5	2025-10-06 22:47:42.28832	create	EventPermission	17	\N	{"id": 17, "event_id": 12, "user_id": 2, "user_username": "jorair", "created_at": "2025-10-06T22:47:42.280852", "updated_at": "2025-10-06T22:47:42.280855"}	Permissão de acesso ao evento 'INAUGURAÇÃO TEMPLO BELVEDERE ' concedida ao usuário ID 2.
74	5	2025-10-06 22:47:47.534406	create	EventPermission	18	\N	{"id": 18, "event_id": 12, "user_id": 3, "user_username": "felipe", "created_at": "2025-10-06T22:47:47.528213", "updated_at": "2025-10-06T22:47:47.528216"}	Permissão de acesso ao evento 'INAUGURAÇÃO TEMPLO BELVEDERE ' concedida ao usuário ID 3.
75	5	2025-10-06 22:59:16.0612	update	Task	6	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "cdc4574f-5e11-45b8-8af2-91747a54733f.webm", "audio_duration_seconds": 31, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [3], "assigned_usernames": ["felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T22:41:53.428850", "attachments_count": 0}	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "cdc4574f-5e11-45b8-8af2-91747a54733f.webm", "audio_duration_seconds": 31, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [null, null, null, null], "assigned_usernames": ["admin", "admin", "felipe", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T22:41:53.428850", "attachments_count": 0}	Tarefa 'Preparativos para o Evento' atualizada no evento 'INAUGURAÇÃO TEMPLO BELVEDERE '.
76	5	2025-10-06 23:00:43.178079	create	Comment	26	\N	{"id": 26, "content": "@luis.estiano Crie as tarefas para seu pessoal e vincula o usu\\u00e1rio, para eles terem acesso ao evento. Se n\\u00e3o vincular, n\\u00e3o aparecer\\u00e1 para eles.", "timestamp": "2025-10-06T23:00:43.163354", "task_id": 6, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Preparativos para o Evento'.
77	5	2025-10-06 23:01:54.106534	create	Attachment	4	\N	{"id": 4, "task_id": 6, "filename": "Captura_de_tela_2025-10-06_185811.png", "unique_filename": "5bcbdbc2-e92f-4e75-8e48-ac89e110fac0.png", "storage_path": "/opt/render/project/src/instance/uploads/attachments/5bcbdbc2-e92f-4e75-8e48-ac89e110fac0.png", "mimetype": "image/png", "filesize": 25853, "uploaded_by_user_id": 5, "uploaded_by_username": "jaime", "upload_timestamp": "2025-10-06T23:01:54.100427", "download_url": "/attachment/4/download"}	Anexo 'Captura_de_tela_2025-10-06_185811.png' adicionado à tarefa 'Preparativos para o Evento' por jaime.
78	5	2025-10-06 23:02:11.093574	create	Comment	27	\N	{"id": 27, "content": "Anexei um print da tela pra vc ver onde faz a inclus\\u00e3o", "timestamp": "2025-10-06T23:02:11.086618", "task_id": 6, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Preparativos para o Evento'.
79	3	2025-10-06 23:04:37.44877	update	Task	6	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "cdc4574f-5e11-45b8-8af2-91747a54733f.webm", "audio_duration_seconds": 31, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 3], "assigned_usernames": ["admin", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T22:41:53.428850", "attachments_count": 1}	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "d26cf031-57cf-4b69-b9cd-e32d4dc94263.webm", "audio_duration_seconds": 21, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 3], "assigned_usernames": ["admin", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T23:04:37.435820", "attachments_count": 1}	Áudio adicionado/atualizado na tarefa 'Preparativos para o Evento'. Duração: 21s.
80	3	2025-10-06 23:05:35.114364	update	Task	6	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "d26cf031-57cf-4b69-b9cd-e32d4dc94263.webm", "audio_duration_seconds": 21, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 3], "assigned_usernames": ["admin", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T23:04:37.435820", "attachments_count": 1}	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "50b6c66c-0c56-4ffc-a6ec-4bbca0f9887a.webm", "audio_duration_seconds": 11, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 3], "assigned_usernames": ["admin", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T23:05:35.097423", "attachments_count": 1}	Áudio adicionado/atualizado na tarefa 'Preparativos para o Evento'. Duração: 11s.
89	5	2025-10-07 13:57:03.421704	update	Event	2	{"id": 2, "title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)", "description": "", "due_date": "2025-09-29T08:30:00", "end_date": "2025-09-29T12:01:00", "location": "Audit\\u00f3rio A1", "author_id": 1, "category_id": 2, "status_id": 3, "status_name": "Arquivado", "created_at": "2025-09-24T00:48:13.099891", "updated_at": "2025-10-06T22:27:34.226004", "is_published": true, "is_cancelled": false}	{"id": 2, "title": "REUNI\\u00c3O MINISTERIAL DOS SETORES DE CUIAB\\u00c1 E REGI\\u00c3O 8H30 (A1)", "description": "", "due_date": "2025-09-29T08:30:00", "end_date": "2025-09-29T12:01:00", "location": "AUDIT\\u00d3RIO A1", "author_id": 1, "category_id": 2, "status_id": 3, "status_name": "Arquivado", "created_at": "2025-09-24T00:48:13.099891", "updated_at": "2025-10-07T13:57:03.410711", "is_published": true, "is_cancelled": false}	Evento 'REUNIÃO MINISTERIAL DOS SETORES DE CUIABÁ E REGIÃO 8H30 (A1)' atualizado.
81	5	2025-10-06 23:16:05.780487	update	Task	6	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "50b6c66c-0c56-4ffc-a6ec-4bbca0f9887a.webm", "audio_duration_seconds": 11, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 3], "assigned_usernames": ["admin", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T23:05:35.097423", "attachments_count": 1}	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "50b6c66c-0c56-4ffc-a6ec-4bbca0f9887a.webm", "audio_duration_seconds": 11, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [null, null, null, null, null, null], "assigned_usernames": ["admin", "admin", "Jamilly", "Jamilly", "felipe", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T23:05:35.097423", "attachments_count": 1}	Tarefa 'Preparativos para o Evento' atualizada no evento 'INAUGURAÇÃO TEMPLO BELVEDERE '.
82	5	2025-10-06 23:19:26.187987	update	Task	6	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "50b6c66c-0c56-4ffc-a6ec-4bbca0f9887a.webm", "audio_duration_seconds": 11, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 6, 3], "assigned_usernames": ["admin", "Jamilly", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T23:05:35.097423", "attachments_count": 1}	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "50b6c66c-0c56-4ffc-a6ec-4bbca0f9887a.webm", "audio_duration_seconds": 11, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [null, null, null, null], "assigned_usernames": ["admin", "admin", "felipe", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T23:05:35.097423", "attachments_count": 1}	Tarefa 'Preparativos para o Evento' atualizada no evento 'INAUGURAÇÃO TEMPLO BELVEDERE '.
83	5	2025-10-07 10:13:22.106029	create	Comment	28	\N	{"id": 28, "content": "@felipe @jorair conseguem acompanhar essa tarefa?", "timestamp": "2025-10-07T10:13:22.098053", "task_id": 6, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Preparativos para o Evento'.
84	5	2025-10-07 10:14:02.679956	create	Comment	29	\N	{"id": 29, "content": "@admin", "timestamp": "2025-10-07T10:14:02.672450", "task_id": 6, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Preparativos para o Evento'.
85	5	2025-10-07 13:48:31.242564	update	Event	11	{"id": 11, "title": "Batismo", "description": "", "due_date": "2025-09-28T10:00:00", "end_date": "2025-09-28T12:00:00", "location": "Grande Templo", "author_id": 2, "category_id": 2, "status_id": 3, "status_name": "Arquivado", "created_at": "2025-09-24T20:14:05.739913", "updated_at": "2025-09-29T23:45:03.728677", "is_published": false, "is_cancelled": false}	{"id": 11, "title": "BATISMO", "description": "", "due_date": "2025-09-28T10:00:00", "end_date": "2025-09-28T12:00:00", "location": "GRANDE TEMPLO", "author_id": 2, "category_id": 2, "status_id": 3, "status_name": "Arquivado", "created_at": "2025-09-24T20:14:05.739913", "updated_at": "2025-10-07T13:48:31.226898", "is_published": false, "is_cancelled": false}	Evento 'BATISMO' atualizado.
86	5	2025-10-07 13:49:00.507365	update	Event	6	{"id": 6, "title": "Reuni\\u00e3o de Obreiros - Cuiab\\u00e1 e Regi\\u00e3o - 08h30 (N)", "description": "", "due_date": "2025-10-11T08:30:00", "end_date": "2025-10-11T12:00:00", "location": "Nave - Grande Templo", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:52:41.186919", "updated_at": "2025-10-06T22:27:26.358006", "is_published": true, "is_cancelled": false}	{"id": 6, "title": "REUNI\\u00c3O DE OBREIROS - CUIAB\\u00c1 E REGI\\u00c3O - 08H30 (N)", "description": "", "due_date": "2025-10-11T08:30:00", "end_date": "2025-10-11T12:00:00", "location": "NAVE - GRANDE TEMPLO", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:52:41.186919", "updated_at": "2025-10-07T13:49:00.499214", "is_published": true, "is_cancelled": false}	Evento 'REUNIÃO DE OBREIROS - CUIABÁ E REGIÃO - 08H30 (N)' atualizado.
87	5	2025-10-07 13:49:23.717247	update	Event	3	{"id": 3, "title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)", "description": "", "due_date": "2025-10-27T08:30:00", "end_date": "2025-10-27T08:30:00", "location": "Audit\\u00f3rio A1", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:49:27.957798", "updated_at": "2025-10-06T22:28:21.344333", "is_published": true, "is_cancelled": false}	{"id": 3, "title": "REUNI\\u00c3O MINISTERIAL DOS SETORES DE CUIAB\\u00c1 E REGI\\u00c3O 8H30 (A1)", "description": "", "due_date": "2025-10-27T08:30:00", "end_date": "2025-10-27T08:30:00", "location": "AUDIT\\u00d3RIO A1", "author_id": 1, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-09-24T00:49:27.957798", "updated_at": "2025-10-07T13:49:23.709388", "is_published": true, "is_cancelled": false}	Evento 'REUNIÃO MINISTERIAL DOS SETORES DE CUIABÁ E REGIÃO 8H30 (A1)' atualizado.
88	5	2025-10-07 13:49:39.949816	update	Event	12	{"id": 12, "title": "INAUGURA\\u00c7\\u00c3O TEMPLO BELVEDERE ", "description": "", "due_date": "2025-11-09T09:00:00", "end_date": "2025-11-09T12:00:00", "location": "R. Martim Pescador - Res. Maria de Lourdes, Cuiab\\u00e1 - MT", "author_id": 5, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-10-06T22:32:39.118571", "updated_at": "2025-10-06T22:33:12.407056", "is_published": true, "is_cancelled": false}	{"id": 12, "title": "INAUGURA\\u00c7\\u00c3O TEMPLO BELVEDERE ", "description": "", "due_date": "2025-11-09T09:00:00", "end_date": "2025-11-09T12:00:00", "location": "R. MARTIM PESCADOR - RES. MARIA DE LOURDES, CUIAB\\u00c1 - MT", "author_id": 5, "category_id": 2, "status_id": 1, "status_name": "Ativo", "created_at": "2025-10-06T22:32:39.118571", "updated_at": "2025-10-07T13:49:39.941609", "is_published": true, "is_cancelled": false}	Evento 'INAUGURAÇÃO TEMPLO BELVEDERE ' atualizado.
90	3	2025-10-07 13:58:22.423886	update	Task	6	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "50b6c66c-0c56-4ffc-a6ec-4bbca0f9887a.webm", "audio_duration_seconds": 11, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 3], "assigned_usernames": ["admin", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-06T23:05:35.097423", "attachments_count": 1}	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "50b6c66c-0c56-4ffc-a6ec-4bbca0f9887a.webm", "audio_duration_seconds": 11, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 3], "assigned_usernames": ["admin", "felipe"], "is_completed": true, "completed_at": "2025-10-07T13:58:22.404634", "completed_by_id": 3, "completed_by_username": "felipe", "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-07T13:58:22.406162", "attachments_count": 1}	Tarefa 'Preparativos para o Evento' concluída por felipe. Comentário: 'Pastor Jaime senhor já informou o protocolo de inauguração para eles ? '
91	3	2025-10-07 13:58:40.54137	update	Task	6	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "50b6c66c-0c56-4ffc-a6ec-4bbca0f9887a.webm", "audio_duration_seconds": 11, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 3], "assigned_usernames": ["admin", "felipe"], "is_completed": true, "completed_at": "2025-10-07T13:58:22.404634", "completed_by_id": 3, "completed_by_username": "felipe", "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-07T13:58:22.406162", "attachments_count": 1}	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "50b6c66c-0c56-4ffc-a6ec-4bbca0f9887a.webm", "audio_duration_seconds": 11, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 3], "assigned_usernames": ["admin", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-07T13:58:40.528096", "attachments_count": 1}	Tarefa 'Preparativos para o Evento' marcada como não concluída por felipe.
92	5	2025-10-07 14:07:27.869857	update	Task	6	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "50b6c66c-0c56-4ffc-a6ec-4bbca0f9887a.webm", "audio_duration_seconds": 11, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 3], "assigned_usernames": ["admin", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-07T13:58:40.528096", "attachments_count": 1}	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "10e8bc28-ea87-485e-be64-3d2369ea70a1.webm", "audio_duration_seconds": 5, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 3], "assigned_usernames": ["admin", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-07T14:07:27.772659", "attachments_count": 1}	Áudio adicionado/atualizado na tarefa 'Preparativos para o Evento'. Duração: 5s.
93	5	2025-10-07 14:08:38.133582	create	Comment	30	\N	{"id": 30, "content": "@jorair @luis.estiano ol\\u00e1", "timestamp": "2025-10-07T14:08:38.114908", "task_id": 6, "user_id": 5, "username": "jaime"}	Comentário adicionado por 'jaime' na tarefa 'Preparativos para o Evento'.
94	1	2025-10-07 14:16:58.493018	create	Comment	31	\N	{"id": 31, "content": "@jaime teste", "timestamp": "2025-10-07T14:16:58.483372", "task_id": 6, "user_id": 1, "username": "admin"}	Comentário adicionado por 'admin' na tarefa 'Preparativos para o Evento'.
95	5	2025-10-07 15:08:28.725612	delete	Attachment	4	{"id": 4, "task_id": 6, "filename": "Captura_de_tela_2025-10-06_185811.png", "unique_filename": "5bcbdbc2-e92f-4e75-8e48-ac89e110fac0.png", "storage_path": "/opt/render/project/src/instance/uploads/attachments/5bcbdbc2-e92f-4e75-8e48-ac89e110fac0.png", "mimetype": "image/png", "filesize": 25853, "uploaded_by_user_id": 5, "uploaded_by_username": "jaime", "upload_timestamp": "2025-10-06T23:01:54.100427", "download_url": "/attachment/4/download"}	\N	Anexo 'Captura_de_tela_2025-10-06_185811.png' excluído da tarefa 'Preparativos para o Evento' por jaime.
96	3	2025-10-09 14:48:51.901116	update	Task	6	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "10e8bc28-ea87-485e-be64-3d2369ea70a1.webm", "audio_duration_seconds": 5, "event_id": 12, "task_status_id": 5, "task_status_name": "N\\u00e3o Iniciado", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 3], "assigned_usernames": ["admin", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-07T14:07:27.772659", "attachments_count": 0}	{"id": 6, "title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "notes": "Documentos j\\u00e1 solicitados e encaminhado para o Leonardo produzir o banner ", "due_date": "2025-11-09T09:00:00", "original_due_date": "2025-11-09T09:00:00", "cloud_storage_link": "", "link_notes": "", "audio_path": "10e8bc28-ea87-485e-be64-3d2369ea70a1.webm", "audio_duration_seconds": 5, "event_id": 12, "task_status_id": 5, "task_status_name": "Em Andamento", "task_category_id": 3, "task_category_name": "Produ\\u00e7\\u00e3o", "assigned_user_ids": [1, 3], "assigned_usernames": ["admin", "felipe"], "is_completed": false, "completed_at": null, "completed_by_id": null, "completed_by_username": null, "created_at": "2025-10-06T22:40:22.186842", "updated_at": "2025-10-07T14:07:27.772659", "attachments_count": 0}	Tarefa 'Preparativos para o Evento' atualizada no evento 'INAUGURAÇÃO TEMPLO BELVEDERE '.
\.


--
-- Data for Name: comment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.comment (id, content, "timestamp", task_id, user_id) FROM stdin;
3	Confirmar fotógrafos	2025-09-25 02:38:45.277992	2	1
4	Jorair, os comentários aqui são guardados e enviados para o email. Depois irei melhorar a lógica e implementar o @menção assim as mensagem seguem somente quando houver menção da pessoa.	2025-09-25 22:38:37.39883	2	5
5	Assim que ler essa mensagem, retorne aqui, por gentileza..	2025-09-25 22:40:08.713127	2	5
6	Pastor o @jorair ja confirmou com o donato a cobertura fotografica	2025-09-26 15:27:28.571899	2	3
7	@Julia chegou de verificar mais pessoas para escala ?	2025-09-26 15:27:58.192435	5	3
8	Pastor Jaime, os fotógrafos já estão convocados.\nComo criei um grupo no whats pra alinhamento, já havia feito a convocação e alinhamento por lá.\n\nSerão Ellen, Jane e Donato	2025-09-27 12:20:54.3825	2	2
9	@julia @felipe	2025-09-27 23:54:27.587967	5	5
10	@luis.estiano como está para amanhã?	2025-09-27 23:54:50.693378	5	5
11	@jorair está funcionando agora a menção  "@name_do_usuario"	2025-09-28 00:01:56.73501	2	5
12	@admin teste mensagem	2025-09-29 17:11:41.868027	5	5
13	@admin teste mensagem	2025-09-29 17:11:52.557	5	5
14	@admin teste mensagem	2025-09-29 17:11:54.654673	5	5
15	@admin teste mensagem	2025-09-29 17:12:00.721744	5	5
16	@admin teste mensagem	2025-09-29 17:12:07.987965	5	5
17	@admin teste mensagem	2025-09-29 17:12:14.539995	5	5
18	@felipe tudo certo com a cobertura?	2025-09-29 17:36:07.949205	5	5
19	@felipe tudo certo então?	2025-09-29 18:33:12.961915	5	5
20	@admin teste	2025-09-29 18:34:25.316383	5	5
21	@admin teste	2025-09-29 18:36:34.74791	3	5
22	@admin teste	2025-09-29 18:36:34.783527	3	5
23	@admin	2025-09-29 18:37:56.888791	2	5
24	@admin esta ok	2025-09-29 22:33:01.411173	2	5
25	@julia finalizar	2025-09-29 22:35:21.543134	5	5
26	@luis.estiano Crie as tarefas para seu pessoal e vincula o usuário, para eles terem acesso ao evento. Se não vincular, não aparecerá para eles.	2025-10-06 23:00:43.163354	6	5
27	Anexei um print da tela pra vc ver onde faz a inclusão	2025-10-06 23:02:11.086618	6	5
28	@felipe @jorair conseguem acompanhar essa tarefa?	2025-10-07 10:13:22.098053	6	5
29	@admin	2025-10-07 10:14:02.67245	6	5
30	@jorair @luis.estiano olá	2025-10-07 14:08:38.114908	6	5
31	@jaime teste	2025-10-07 14:16:58.483372	6	1
\.


--
-- Data for Name: event; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.event (id, title, description, due_date, end_date, location, created_at, updated_at, author_id, category_id, status_id, is_published, is_cancelled) FROM stdin;
4	Reunião Ministerial dos Setores de Cuiabá e Região 8h30 (A1)		2025-11-24 08:30:00	2025-11-24 08:30:00	Auditório A1	2025-09-24 00:50:29.035299	2025-09-24 00:50:29.035302	1	2	1	f	f
5	Reunião Ministerial dos Setores de Cuiabá e Região 8h30 (A1)		2025-12-29 08:30:00	2025-12-29 12:00:00	Auditório A1	2025-09-24 00:51:18.650557	2025-09-24 00:51:18.65056	1	2	1	f	f
7	Reunião de Obreiros - Cuiabá e Região - 08h30 (N)		2025-11-08 08:30:00	2025-11-08 08:30:00	Nave - Grande Templo	2025-09-24 00:53:34.075777	2025-09-24 00:53:34.07578	1	2	1	f	f
8	Reunião de Obreiros - Cuiabá e Região - 08h30 (N)		2025-11-08 08:30:00	2025-11-08 08:30:00	Nave - Grande Templo	2025-09-24 00:53:34.161343	2025-09-24 00:53:34.161346	1	2	1	f	f
9	Reunião de Obreiros - Cuiabá e Região - 08h30 (N)		2025-12-13 08:30:00	2025-12-13 12:00:00	Nave - Grande Templo	2025-09-24 00:54:09.482586	2025-09-24 00:54:09.482589	1	2	1	f	f
10	83ª AGO/COMADEMAT 19h		2025-11-04 19:00:00	2025-11-07 12:00:00	Nave - Grande Templo	2025-09-24 00:56:17.269211	2025-09-24 00:56:17.269214	1	3	1	f	f
11	BATISMO		2025-09-28 10:00:00	2025-09-28 12:00:00	GRANDE TEMPLO	2025-09-24 20:14:05.739913	2025-10-07 13:48:31.226898	2	2	3	f	f
6	REUNIÃO DE OBREIROS - CUIABÁ E REGIÃO - 08H30 (N)		2025-10-11 08:30:00	2025-10-11 12:00:00	NAVE - GRANDE TEMPLO	2025-09-24 00:52:41.186919	2025-10-07 13:49:00.499214	1	2	1	t	f
3	REUNIÃO MINISTERIAL DOS SETORES DE CUIABÁ E REGIÃO 8H30 (A1)		2025-10-27 08:30:00	2025-10-27 08:30:00	AUDITÓRIO A1	2025-09-24 00:49:27.957798	2025-10-07 13:49:23.709388	1	2	1	t	f
12	INAUGURAÇÃO TEMPLO BELVEDERE 		2025-11-09 09:00:00	2025-11-09 12:00:00	R. MARTIM PESCADOR - RES. MARIA DE LOURDES, CUIABÁ - MT	2025-10-06 22:32:39.118571	2025-10-07 13:49:39.941609	5	2	1	t	f
2	REUNIÃO MINISTERIAL DOS SETORES DE CUIABÁ E REGIÃO 8H30 (A1)		2025-09-29 08:30:00	2025-09-29 12:01:00	AUDITÓRIO A1	2025-09-24 00:48:13.099891	2025-10-07 13:57:03.410711	1	2	3	t	f
\.


--
-- Data for Name: event_permission; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.event_permission (id, event_id, user_id, created_at, updated_at) FROM stdin;
2	10	2	2025-09-25 22:22:56.85919	2025-09-25 22:22:56.859193
3	2	19	2025-09-25 22:24:17.43712	2025-09-25 22:24:17.437123
4	2	2	2025-09-25 22:24:28.546204	2025-09-25 22:24:28.546208
5	2	3	2025-09-25 22:24:36.787029	2025-09-25 22:24:36.787032
6	6	2	2025-09-25 22:25:06.395079	2025-09-25 22:25:06.395083
7	6	3	2025-09-25 22:25:17.103923	2025-09-25 22:25:17.103926
8	6	19	2025-09-25 22:25:23.12088	2025-09-25 22:25:23.120884
9	3	19	2025-09-25 22:26:08.05052	2025-09-25 22:26:08.050523
10	3	2	2025-09-25 22:26:15.475273	2025-09-25 22:26:15.475276
11	3	3	2025-09-25 22:26:23.798667	2025-09-25 22:26:23.79867
12	10	19	2025-09-25 22:26:42.644773	2025-09-25 22:26:42.644777
13	10	3	2025-09-25 22:26:50.247655	2025-09-25 22:26:50.247658
14	11	3	2025-09-25 22:28:59.217683	2025-09-25 22:28:59.217687
15	11	19	2025-09-25 22:29:10.323292	2025-09-25 22:29:10.323295
16	11	2	2025-09-25 22:29:24.76419	2025-09-25 22:29:24.764193
17	12	2	2025-10-06 22:47:42.280852	2025-10-06 22:47:42.280855
18	12	3	2025-10-06 22:47:47.528213	2025-10-06 22:47:47.528216
\.


--
-- Data for Name: group; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public."group" (id, name, description, created_at, updated_at) FROM stdin;
\.


--
-- Data for Name: notification; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.notification (id, user_id, message, link_url, is_read, "timestamp", related_object_type, related_object_id) FROM stdin;
5	12	'felipe' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	f	2025-09-26 15:27:58.45227	Task	5
7	12	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	f	2025-09-27 23:54:27.61617	Task	5
10	12	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	f	2025-09-27 23:54:50.711383	Task	5
11	4	Você foi mencionado por 'jaime' no comentário da tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	f	2025-09-27 23:54:50.889058	Task	5
21	12	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	f	2025-09-29 17:36:08.067873	Task	5
8	3	Você foi mencionado por 'jaime' no comentário da tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	t	2025-09-27 23:54:27.796144	Task	5
20	3	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	t	2025-09-29 17:36:08.066289	Task	5
24	12	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	f	2025-09-29 18:33:12.973784	Task	5
27	12	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	f	2025-09-29 18:34:25.329569	Task	5
28	1	Você foi mencionado por 'jaime' no comentário da tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	t	2025-09-29 18:34:25.461468	Task	5
29	1	'jaime' comentou na tarefa 'Registro Imagens'.	https://gerenciador-eventos-ea68.onrender.com/task/3	t	2025-09-29 18:36:34.756653	Task	3
30	1	'jaime' comentou na tarefa 'Registro Imagens'.	https://gerenciador-eventos-ea68.onrender.com/task/3	t	2025-09-29 18:36:34.792564	Task	3
32	1	Você foi mencionado por 'jaime' no comentário da tarefa 'Registro Fotográfico'.	https://gerenciador-eventos-ea68.onrender.com/task/2	t	2025-09-29 18:37:57.018904	Task	2
34	1	Você foi mencionado por 'jaime' no comentário da tarefa 'Registro Fotográfico'.	https://gerenciador-eventos-ea68.onrender.com/task/2	t	2025-09-29 22:33:01.624118	Task	2
37	12	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	f	2025-09-29 22:35:21.557722	Task	5
1	2	'jaime' comentou na tarefa 'Registro Fotográfico'.	https://gerenciador-eventos-ea68.onrender.com/task/2	t	2025-09-25 22:38:37.568247	Task	2
2	2	'jaime' comentou na tarefa 'Registro Fotográfico'.	https://gerenciador-eventos-ea68.onrender.com/task/2	t	2025-09-25 22:40:08.851203	Task	2
3	2	'felipe' comentou na tarefa 'Registro Fotográfico'.	https://gerenciador-eventos-ea68.onrender.com/task/2	t	2025-09-26 15:27:28.713002	Task	2
4	2	'felipe' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	t	2025-09-26 15:27:58.452266	Task	5
6	2	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	t	2025-09-27 23:54:27.616166	Task	5
9	2	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	t	2025-09-27 23:54:50.71138	Task	5
12	2	'jaime' comentou na tarefa 'Registro Fotográfico'.	https://gerenciador-eventos-ea68.onrender.com/task/2	t	2025-09-28 00:01:56.752413	Task	2
19	2	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	t	2025-09-29 17:36:08.064037	Task	5
22	2	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	t	2025-09-29 18:33:12.970586	Task	5
25	2	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	t	2025-09-29 18:34:25.324843	Task	5
31	2	'jaime' comentou na tarefa 'Registro Fotográfico'.	https://gerenciador-eventos-ea68.onrender.com/task/2	t	2025-09-29 18:37:56.896277	Task	2
33	2	'jaime' comentou na tarefa 'Registro Fotográfico'.	https://gerenciador-eventos-ea68.onrender.com/task/2	t	2025-09-29 22:33:01.444967	Task	2
35	2	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	t	2025-09-29 22:35:21.557717	Task	5
23	3	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	t	2025-09-29 18:33:12.971995	Task	5
26	3	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	t	2025-09-29 18:34:25.326366	Task	5
36	3	'jaime' comentou na tarefa 'Edição Conteúdo '.	https://gerenciador-eventos-ea68.onrender.com/task/5	t	2025-09-29 22:35:21.55772	Task	5
40	4	Você foi mencionado por 'jaime' no comentário da tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	f	2025-10-06 23:00:43.323075	Task	6
38	1	'jaime' comentou na tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-06 23:00:43.17933	Task	6
41	1	'jaime' comentou na tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-06 23:02:11.0942	Task	6
43	1	'jaime' comentou na tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-07 10:13:22.106679	Task	6
46	1	'jaime' comentou na tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-07 10:14:02.680926	Task	6
51	4	Você foi mencionado por 'jaime' no comentário da tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	f	2025-10-07 14:08:38.51112	Task	6
39	3	'jaime' comentou na tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-06 23:00:43.179334	Task	6
42	3	'jaime' comentou na tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-06 23:02:11.094203	Task	6
44	3	'jaime' comentou na tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-07 10:13:22.106681	Task	6
48	1	'jaime' comentou na tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-07 14:08:38.135118	Task	6
53	5	'admin' comentou na tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-07 14:16:58.496371	Task	6
45	2	Você foi mencionado por 'jaime' no comentário da tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-07 10:13:22.23103	Task	6
50	2	Você foi mencionado por 'jaime' no comentário da tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-07 14:08:38.328875	Task	6
47	3	'jaime' comentou na tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-07 10:14:02.680933	Task	6
49	3	'jaime' comentou na tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-07 14:08:38.138278	Task	6
52	3	'admin' comentou na tarefa 'Preparativos para o Evento'.	https://gerenciador-eventos-ea68.onrender.com/task/6	t	2025-10-07 14:16:58.494132	Task	6
\.


--
-- Data for Name: password_reset_token; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.password_reset_token (id, token_uuid, user_id, expiration_date, is_used, created_at) FROM stdin;
\.


--
-- Data for Name: push_subscription; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.push_subscription (id, user_id, endpoint, p256dh, auth, "timestamp") FROM stdin;
1	5	https://fcm.googleapis.com/fcm/send/c2H5M7yVXbc:APA91bFT15cVxqrd76rp4p0PAxttlC0b8qx6iZD8ory3YXY7YVABRCgF0b18WF72cEm1kAneyClBepC_FowtKQZIO-Jewigrk7uwMZL_UIlIkxewFbrgCvSxqM1jlvTf7TXG0ZgM4XWg	BEbNih99RqwISgakmyQcJfrWXLzcTqFnFz4AMPrAE3cSuIh842bUZh0sddmdJfJ-UfeNu9UNmPI5Jx5MCZEzwoc	oUfM5XQefmYP2knLtJLKGw	2025-09-29 17:35:11.23999
30	5	https://fcm.googleapis.com/fcm/send/faRp6X3wZ9I:APA91bHS7c7rGkHP9Qb5teXQ7NyESXW240mHJJqmoBkNblOM8KJI_M8jDZyKMV_WZpRLthCcrVIlFRwEPGdiAKukQu1eQbcNrfiTM_G0DE8e2GdbGnwQlVmEu7-2GMyTXSb1Ymj1Nf7f	BBwnOVoPc7tQlVxyX5WEnQgwTFflenOQEHVdCjVs-HXzUr_NwUCXyePQmhb97RUzv6phl3UJdZy_HNNXtmg1DZI	ntVVWDk6z0nf3eE6EDbrwA	2025-10-07 13:46:28.087007
2	5	https://fcm.googleapis.com/fcm/send/eUJ5iSn3KG0:APA91bEopuxARZfI6X03WiCu-fnUD4M-TtAP5wfU4x8pDX1FXndYPfKhstuHbq82xLb2CpxX8lus2v86ADyuWIyQx5pE4k48wJOoobO50by_SgjfgFLnDtagesnhPh4zEBws3llmj2vJ	BFX8cRJaFOREGf9elvHpbA-VRe3dEIzv7JBz_rlQEI-g4gHLwaJx-tzuVMPR0nnUDnLV1EKmzKuhoCdl5ifpNGg	1feaLwZ0UJMlOhW9QCcG8A	2025-10-09 12:30:24.287204
\.


--
-- Data for Name: role; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.role (id, name, description, can_view_event, can_edit_event, can_manage_permissions, can_create_event, can_create_task, can_edit_task, can_delete_task, can_complete_task, can_uncomplete_task, can_upload_task_audio, can_delete_task_audio, can_view_task_history, can_manage_task_comments, can_upload_attachments, can_manage_attachments, can_publish_event, can_cancel_event, can_duplicate_event, can_view_event_registrations, can_view_event_reports) FROM stdin;
1	Admin	Administrator role with full access	t	t	t	t	t	t	t	t	t	t	t	t	t	t	t	f	f	f	f	f
2	Usuário		t	f	f	f	t	t	f	t	t	t	f	t	t	t	t	f	f	f	f	f
3	Coordenador Equipe	 	t	t	f	f	t	t	t	t	t	t	t	t	t	t	t	f	f	f	f	f
4	Gerente de Projeto		t	t	f	t	t	t	t	t	t	t	t	t	t	t	t	f	f	f	f	f
\.


--
-- Data for Name: status; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.status (id, name, type, description) FROM stdin;
1	Ativo	event	Em atividade
2	Finalizado	event	 
3	Arquivado	event	
5	Não Iniciado	task	
4	Em Andamento	task	
6	Concluido	task	
7	Finalizado	task	
\.


--
-- Data for Name: task; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.task (id, title, description, notes, due_date, original_due_date, cloud_storage_link, link_notes, audio_path, audio_duration_seconds, created_at, updated_at, event_id, task_status_id, task_category_id, is_completed, completed_at, completed_by_id) FROM stdin;
3	Registro Imagens	Verificar quais conteúdos serão criados 		2025-09-25 12:00:00	2025-09-25 12:00:00			\N	\N	2025-09-24 21:23:54.500719	2025-09-24 21:23:54.500722	2	5	\N	f	\N	\N
4	Cobertura			2025-12-26 10:08:00	2025-12-26 10:08:00			\N	\N	2025-09-25 14:11:22.20979	2025-09-25 14:11:22.209793	5	6	5	f	\N	\N
5	Edição Conteúdo 	Júlia, verificar as capas para os posts		2025-09-27 13:00:00	2025-09-27 13:00:00			\N	\N	2025-09-25 22:50:32.513119	2025-09-25 22:50:32.513121	11	5	3	f	\N	\N
2	Registro Fotográfico			2025-09-28 13:00:00	2025-09-28 13:00:00	https://drive.google.com/drive/folders/1XB6I3JcD4ZJ6XQFB_20ZFc5Dylh_8cA7?usp=sharing		\N	\N	2025-09-24 20:15:16.604	2025-09-30 19:18:23.72273	11	5	1	t	2025-09-30 19:18:23.72086	2
7	Escala da Equipe para o Evento			2025-10-10 12:00:00	2025-10-10 12:00:00			df2ae5af-e637-4476-87e8-fbeddf33ed2a.webm	24	2025-10-06 22:46:04.643012	2025-10-06 22:46:44.159443	12	5	5	f	\N	\N
6	Preparativos para o Evento	Pedir todas as informações ao diácono Gonçalo 65 9949-9356	Documentos já solicitados e encaminhado para o Leonardo produzir o banner 	2025-11-09 09:00:00	2025-11-09 09:00:00			10e8bc28-ea87-485e-be64-3d2369ea70a1.webm	5	2025-10-06 22:40:22.186842	2025-10-09 14:48:51.904304	12	4	3	f	\N	\N
\.


--
-- Data for Name: task_assignment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.task_assignment (task_id, user_id, assigned_at) FROM stdin;
5	12	2025-09-27 23:56:18.9652
5	3	2025-09-27 23:56:18.965204
7	12	2025-10-06 22:46:04.64856
7	19	2025-10-06 22:46:04.648563
6	1	2025-10-06 23:19:26.190662
6	3	2025-10-06 23:19:26.190665
\.


--
-- Data for Name: task_category; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.task_category (id, name, description, created_at, updated_at) FROM stdin;
1	Redes Sociais		2025-09-24 00:39:37.956152	2025-09-24 00:39:37.956157
2	Artes		2025-09-24 00:39:48.351591	2025-09-24 00:39:48.351595
3	Produção		2025-09-24 00:39:57.932905	2025-09-24 00:39:57.932909
4	Tecnologia		2025-09-24 00:40:15.828829	2025-09-24 00:40:15.828833
5	Conteúdo		2025-09-24 00:40:32.295211	2025-09-24 00:40:32.295216
6	ID de Evento	Abrir check-list com todos os materiais padrões para esse tipo de trabalho.	2025-09-25 22:52:28.133976	2025-09-25 22:52:28.133979
7	Inauguração de Templo	Para esse tipo de evento é feita a cobertura completa, com fotos, vídeos e cobertura com reporter. 	2025-10-06 22:56:24.008007	2025-10-06 22:56:24.008011
8	Inauguração de Casa Pastoral		2025-10-06 22:56:39.457491	2025-10-06 22:56:39.457495
\.


--
-- Data for Name: task_history; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.task_history (id, task_id, action_type, description, old_value, new_value, user_id, "timestamp", comment) FROM stdin;
6	2	creation	Tarefa "Registro Fotográfico" criada.	\N	{"title": "Registro Fotogr\\u00e1fico", "description": "", "due_date": "2025-09-28T13:00:00", "status": "N\\u00e3o Iniciado", "task_category": "Redes Sociais", "event_title": "Batismo"}	2	2025-09-24 20:15:16.615876	Criada por jorair
7	3	creation	Tarefa "Registro Imagens" criada.	\N	{"title": "Registro Imagens", "description": "Verificar quais conte\\u00fados ser\\u00e3o criados ", "due_date": "2025-09-25T12:00:00", "status": "N\\u00e3o Iniciado", "task_category": "N/A", "event_title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)"}	5	2025-09-24 21:23:54.511638	Criada por jaime
8	2	updated	Responsáveis pela tarefa alterados	{"assignees": []}	{"assignees": []}	1	2025-09-25 02:38:23.164429	Responsáveis alterados de 'Nenhum' para 'Nenhum'
9	2	updated	Responsáveis pela tarefa alterados	{"assignees": []}	{"assignees": []}	2	2025-09-25 02:57:50.132218	Responsáveis alterados de 'Nenhum' para 'Nenhum'
10	2	updated	Responsáveis pela tarefa alterados	{"assignees": []}	{"assignees": []}	2	2025-09-25 14:10:26.935705	Responsáveis alterados de 'Nenhum' para 'Nenhum'
11	4	creation	Tarefa "Cobertura" criada.	\N	{"title": "Cobertura", "description": "", "due_date": "2025-12-26T10:08:00", "status": "Concluido", "task_category": "Conte\\u00fado", "event_title": "Reuni\\u00e3o Ministerial dos Setores de Cuiab\\u00e1 e Regi\\u00e3o 8h30 (A1)"}	2	2025-09-25 14:11:22.218359	Criada por jorair
12	3	updated	Responsáveis pela tarefa alterados	{"assignees": []}	{"assignees": ["jorair", "jorair"]}	5	2025-09-25 22:05:44.223898	Responsáveis alterados de 'Nenhum' para 'jorair, jorair'
13	3	updated	Responsáveis pela tarefa alterados	{"assignees": ["jorair"]}	{"assignees": []}	5	2025-09-25 22:06:22.209075	Responsáveis alterados de 'jorair' para 'Nenhum'
14	5	creation	Tarefa "Edição Conteúdo " criada.	\N	{"title": "Edi\\u00e7\\u00e3o Conte\\u00fado ", "description": "J\\u00falia, verificar as capas para os posts", "due_date": "2025-09-27T13:00:00", "status": "N\\u00e3o Iniciado", "task_category": "Produ\\u00e7\\u00e3o", "event_title": "Batismo"}	5	2025-09-25 22:50:32.518438	Criada por jaime
15	5	updated	Responsáveis pela tarefa alterados	{"assignees": ["julia"]}	{"assignees": ["felipe", "felipe", "julia", "julia"]}	5	2025-09-27 23:56:18.967662	Responsáveis alterados de 'julia' para 'felipe, felipe, julia, julia'
16	2	conclusao	Tarefa "Registro Fotográfico" marcada como concluída.	{"is_completed": false, "completed_at": null, "completed_by_id": null, "task_status": "N\\u00e3o Iniciado"}	{"is_completed": true, "completed_at": "2025-09-30T19:18:23.720860", "completed_by_id": 2, "task_status": "N/A"}	2	2025-09-30 19:18:23.725774	fotos no Drive
17	6	creation	Tarefa "Preparativos para o Evento" criada.	\N	{"title": "Preparativos para o Evento", "description": "Pedir todas as informa\\u00e7\\u00f5es ao di\\u00e1cono Gon\\u00e7alo 65 9949-9356", "due_date": "2025-11-09T09:00:00", "status": "N\\u00e3o Iniciado", "task_category": "Produ\\u00e7\\u00e3o", "event_title": "INAUGURA\\u00c7\\u00c3O TEMPLO BELVEDERE "}	5	2025-10-06 22:40:22.197262	Criada por jaime
18	6	audio_updated	Áudio da tarefa atualizado	{"audio_path": null, "audio_duration_seconds": null}	{"audio_path": "cdc4574f-5e11-45b8-8af2-91747a54733f.webm", "audio_duration_seconds": 31}	5	2025-10-06 22:41:53.435359	Áudio de 31s adicionado/atualizado na tarefa.
19	7	creation	Tarefa "Escala da Equipe para o Evento" criada.	\N	{"title": "Escala da Equipe para o Evento", "description": "", "due_date": "2025-10-10T12:00:00", "status": "N\\u00e3o Iniciado", "task_category": "Conte\\u00fado", "event_title": "INAUGURA\\u00c7\\u00c3O TEMPLO BELVEDERE "}	5	2025-10-06 22:46:04.649392	Criada por jaime
20	7	audio_updated	Áudio da tarefa atualizado	{"audio_path": null, "audio_duration_seconds": null}	{"audio_path": "df2ae5af-e637-4476-87e8-fbeddf33ed2a.webm", "audio_duration_seconds": 24}	5	2025-10-06 22:46:44.164289	Áudio de 24s adicionado/atualizado na tarefa.
21	6	updated	Responsáveis pela tarefa alterados	{"assignees": ["felipe"]}	{"assignees": ["admin", "admin", "felipe", "felipe"]}	5	2025-10-06 22:59:16.063358	Responsáveis alterados de 'felipe' para 'admin, admin, felipe, felipe'
22	6	audio_updated	Áudio da tarefa atualizado	{"audio_path": "cdc4574f-5e11-45b8-8af2-91747a54733f.webm", "audio_duration_seconds": 31}	{"audio_path": "d26cf031-57cf-4b69-b9cd-e32d4dc94263.webm", "audio_duration_seconds": 21}	3	2025-10-06 23:04:37.440329	Áudio de 21s adicionado/atualizado na tarefa.
23	6	audio_updated	Áudio da tarefa atualizado	{"audio_path": "d26cf031-57cf-4b69-b9cd-e32d4dc94263.webm", "audio_duration_seconds": 21}	{"audio_path": "50b6c66c-0c56-4ffc-a6ec-4bbca0f9887a.webm", "audio_duration_seconds": 11}	3	2025-10-06 23:05:35.103794	Áudio de 11s adicionado/atualizado na tarefa.
24	6	updated	Responsáveis pela tarefa alterados	{"assignees": ["admin", "felipe"]}	{"assignees": ["Jamilly", "Jamilly", "admin", "admin", "felipe", "felipe"]}	5	2025-10-06 23:16:05.783963	Responsáveis alterados de 'admin, felipe' para 'Jamilly, Jamilly, admin, admin, felipe, felipe'
25	6	updated	Responsáveis pela tarefa alterados	{"assignees": ["Jamilly", "admin", "felipe"]}	{"assignees": ["admin", "admin", "felipe", "felipe"]}	5	2025-10-06 23:19:26.191261	Responsáveis alterados de 'Jamilly, admin, felipe' para 'admin, admin, felipe, felipe'
26	6	conclusao	Tarefa "Preparativos para o Evento" marcada como concluída.	{"is_completed": false, "completed_at": null, "completed_by_id": null, "task_status": "N\\u00e3o Iniciado"}	{"is_completed": true, "completed_at": "2025-10-07T13:58:22.404634", "completed_by_id": 3, "task_status": "N/A"}	3	2025-10-07 13:58:22.409878	Pastor Jaime senhor já informou o protocolo de inauguração para eles ? 
27	6	uncompletion	Tarefa "Preparativos para o Evento" marcada como não concluída.	{"is_completed": true, "completed_at": "2025-10-07T13:58:22.404634", "completed_by_id": 3, "task_status": "N\\u00e3o Iniciado"}	{"is_completed": false, "completed_at": null, "completed_by_id": null, "task_status": "N/A"}	3	2025-10-07 13:58:40.530332	Desfeito por felipe
28	6	audio_updated	Áudio da tarefa atualizado	{"audio_path": "50b6c66c-0c56-4ffc-a6ec-4bbca0f9887a.webm", "audio_duration_seconds": 11}	{"audio_path": "10e8bc28-ea87-485e-be64-3d2369ea70a1.webm", "audio_duration_seconds": 5}	5	2025-10-07 14:07:27.785196	Áudio de 5s adicionado/atualizado na tarefa.
29	6	updated	Notas da tarefa alteradas	{"notes": ""}	{"notes": "Documentos j\\u00e1 solicitados e encaminhado para o Leonardo produzir o banner "}	3	2025-10-09 14:48:51.905689	Notas alteradas.
\.


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public."user" (id, username, email, password_hash, role_id, image_file, is_active_db, created_at, updated_at) FROM stdin;
1	admin	admin@example.com	pbkdf2:sha256:1000000$2eIyBZFwtzPCY9ps$cd3f82c484755bfc26cd10d6147ce90c850c388117eb3e0587cc68e10e392f3b	1	default.jpg	t	2025-09-23 23:01:33.641825	2025-09-23 23:01:33.641831
4	luis	luis.ferro@grandetemplo.com.br	scrypt:32768:8:1$CNpbZlyZZkC84gTc$ed16d9a750550a2e9549ebce59798b0ec34177d49066b778d3410fd9d1773a0f604384e5e6a81f17b72ab5217c0bc84cbca56113f84fefc3b44f8165d3e71904	3	default.jpg	t	2025-09-24 00:59:02.312896	2025-09-24 00:59:02.312901
2	jorair	jorair.alberto@grandetemplo.com.br	scrypt:32768:8:1$H3bCgZNDHYHRTQts$cb51c6cd4012427e8b96ab885e4718bf35c2ea08bf591f33e5dd9a5f5f234efcf9f0ece187ac1133b3e34c474532f7d34da1b9338035e28069820cf5d255effb	4	default.jpg	t	2025-09-24 00:57:58.446682	2025-10-06 22:48:34.728245
6	Jamilly	jamilly.mayre@grandetemplo.com.br	scrypt:32768:8:1$Mig7dqmUgkypGeAc$a680f62b6e8372043ca14dd4271f349e88319835729b964a44c0e94869b3cdab8ed285a761d7f550624ea7915ddf0434b5b64422afea158e65e7f36cf264e203	2	default.jpg	t	2025-09-24 18:47:23.938754	2025-09-24 18:47:23.93876
7	amanda	amanda.beatriz@grandetemplo.com.br	scrypt:32768:8:1$A2ipDlDqN6WOPa4K$e77ca0a994c7dc57a7656f3c1fca509b96bd5da3fcc79092e36a2c9b18d4e58464c7d02965976f7a41443b525cf8e2817325c7f0f4829c5a17b5c03d70f227fb	2	default.jpg	t	2025-09-24 18:47:43.75688	2025-09-24 18:47:43.756885
8	rafael	rafael.florentin@grandetemplo.com.br	scrypt:32768:8:1$QAhqWOjxkUtZADAx$d50214fef0082617ff7d9e7a31eee1eb834350a4556ccfee523e42efa71bd0304bfa9ed7858f9f6a6072086d46ca32e272c39b238902a00f5828dba4132071b3	2	default.jpg	t	2025-09-24 18:48:03.421175	2025-09-24 18:48:03.42118
9	kelric	kelric.samuel@grandetemplo.com.br	scrypt:32768:8:1$6guxYoGBglEmqXQx$5802007ab0143e1638078a53883769d27a49d0cc9c415f89cde1efa99b01c6905bbbb16701f43f861c95ecf5cf6ffb02057d02747696ed337533d9c9d6345ab9	2	default.jpg	t	2025-09-24 18:48:25.32583	2025-09-24 18:48:25.325835
10	jefferson	jefferson.magalhaes@grandetemplo.com.br	scrypt:32768:8:1$iV4vlGpuyoUEPTPX$43bfc42b059c446e91e832e86063eccd0ab627150e3c17cca3fa8197da252fbd011888ee336f2a7fdc0287e139093612080ba339c6eaf0a38c7b71085d99b1b5	2	default.jpg	t	2025-09-24 18:48:47.038859	2025-09-24 18:48:47.038864
11	everton	everton.campos@grandetemplo.com.br	scrypt:32768:8:1$Hs4K81Sw7Cgbz5O2$9b2fb71dc2e7a590cf0b5a5140260d08a76c39bfc4339571cd8eda8b685b8b6d0f6f321ca3cbf8d5a93825506ca80a0ffc4f2bec29f9071bb0f9537dc75ade48	2	default.jpg	t	2025-09-24 18:49:10.311039	2025-09-24 18:49:10.311045
12	julia	brenda.julia@grandetemplo.com.br	scrypt:32768:8:1$vf7L9XvnUWy9KhUm$d362a366bc4c2150b31bdc64c9698e132a65c1111c5fb0aa00620e55af4378576db8f8869d84fb679db547a5cac7cd5c0c86010024ef8a30ea730f94e163ff04	2	default.jpg	t	2025-09-24 18:49:35.212813	2025-09-24 18:49:35.212821
13	vytthor	vytthor.alcantara@grandetemplo.com.br	scrypt:32768:8:1$wkrN5HgPvj8pBHFK$34173e2691f2fb3beb5262806e24f7d4bd864c66d58cfa141c426cf133f415895faec1b0948b1ed9ef2517c2e429ab95355ff398dd84d66ef29700c755d336f7	2	default.jpg	t	2025-09-24 18:50:04.513841	2025-09-24 18:50:04.513845
14	eliabe	eliabe.pereira@grandetemplo.com.br	scrypt:32768:8:1$DYec2fuQaAqpVWF9$39ff928fbb9b424c84fddf9387db5a243df28fd821b0bdce0746806b481fdebcce4619e3eb150a1b5107b91cda7e449684c910b08261384a96f4959d0c4d6d04	2	default.jpg	t	2025-09-24 18:50:24.616062	2025-09-24 18:50:24.616067
15	alefy	alefy.nivaldo@grandetemplo.com.br	scrypt:32768:8:1$i1abI0AB1ScydJZv$16406148d1b825337c9e839d92796d9645303b3e59adbed96e0a390c9ef5a3d1d5dcea74585eaef8010384a2f391dcb030e1c7205329286d0404b3f663dedadd	2	default.jpg	t	2025-09-24 18:50:48.417613	2025-09-24 18:50:48.417619
16	vinicius	vinicius.nunes@grandetemplo.com.br	scrypt:32768:8:1$cWEzL1MiA6saFnrI$f39055dffbfa25a72e8d288c8a24d0848cb9531c1fd995c96c43a0c17a18b1f42a1888a903123e3a1cf4dc04dd37de7da3437a7187db78c0fba1c21822200cd9	2	default.jpg	t	2025-09-24 18:51:25.311103	2025-09-24 18:51:25.31111
17	luis.othavio	luis.othavio@grandetemplo.com.br	scrypt:32768:8:1$16ji4VNV4en7oTeV$eb40f2acc101ec5b461fdb108c21826ddce6c278972b3cc45a0339c6dfe43370bd63807c9f60621a9f9817843a12e85981c24475a8389e3539a0ded186e07203	2	default.jpg	t	2025-09-24 18:52:04.512057	2025-09-24 18:52:04.512062
18	luiz.miguel	luiz.miguel@grandetemplo.com.br	scrypt:32768:8:1$srMjvpQfyIx7KqRt$e3e7a57b16a96845dfd9cd8e621ff3eb7633f4499a74e7ded5ff9e4a31ab57d740612acfb4633113e6c9f070df5d86b7e9816d29b26e817a452a162e2031fde8	2	default.jpg	t	2025-09-24 18:52:31.413489	2025-09-24 18:52:31.413494
19	luis.estiano	luis.estiano@grandetemplo.com.br	scrypt:32768:8:1$PAqZ9tyOziziPmpD$0132a304d788f586971b2bbee1d65c2d08cf01d8d563afdc65984ce3f419fb8d603b3613cb22971ca438dc9af143fb194b4f73eed0b9687dc908c9bef39d66ee	4	default.jpg	t	2025-09-24 18:54:19.343441	2025-10-06 22:48:46.710777
20	teste	teste@teste.com	scrypt:32768:8:1$fQl3GY7Xr2OD8d9w$f6e013cf9b84e246fe3aabeab55040d4a9aed7a8ba3cb1615cf8c5f0623dbe8b7549f43f2de1c4341d89a7538072db4174327b60a58c1fbf84a6b7a024ce2d6f	1	default.jpg	t	2025-09-25 22:57:23.086838	2025-09-25 22:57:23.086849
5	jaime	jaimecba@gmail.com	scrypt:32768:8:1$tcAhQkQNlcwDS0Si$742e9815b879562ea155c1d60c37a1163aa36cb9c33f9364182fef6c5352ce680f1f387964c1728ad372c3c1f23203f61937d824602b97ee524d1c216d5cbe23	1	default.jpg	t	2025-09-24 01:06:59.545254	2025-09-29 16:43:12.970315
3	felipe	felipe.rodrigues@grandetemplo.com.br	scrypt:32768:8:1$2Sk7cFJJ7A951pei$ffaf1f2ab0d51c6f3e233bfd452544ac35ab8471ffde54d44695bb6a560b3a24ad19f2273bc9dd96f698d6a108cdc0cf4cbea19d285a646089f8e0b33b35fd14	4	default.jpg	t	2025-09-24 00:58:37.113371	2025-10-06 20:35:42.107417
\.


--
-- Data for Name: user_group; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.user_group (user_id, group_id, assigned_at) FROM stdin;
\.


--
-- Name: attachment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.attachment_id_seq', 4, true);


--
-- Name: category_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.category_id_seq', 3, true);


--
-- Name: change_log_entry_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.change_log_entry_id_seq', 96, true);


--
-- Name: comment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.comment_id_seq', 31, true);


--
-- Name: event_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.event_id_seq', 12, true);


--
-- Name: event_permission_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.event_permission_id_seq', 18, true);


--
-- Name: group_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.group_id_seq', 1, false);


--
-- Name: notification_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.notification_id_seq', 53, true);


--
-- Name: password_reset_token_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.password_reset_token_id_seq', 1, false);


--
-- Name: push_subscription_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.push_subscription_id_seq', 30, true);


--
-- Name: role_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.role_id_seq', 4, true);


--
-- Name: status_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.status_id_seq', 7, true);


--
-- Name: task_category_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.task_category_id_seq', 8, true);


--
-- Name: task_history_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.task_history_id_seq', 29, true);


--
-- Name: task_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.task_id_seq', 7, true);


--
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.user_id_seq', 20, true);


--
-- Name: event_permission _event_user_unique_uc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_permission
    ADD CONSTRAINT _event_user_unique_uc UNIQUE (event_id, user_id);


--
-- Name: status _name_type_uc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status
    ADD CONSTRAINT _name_type_uc UNIQUE (name, type);


--
-- Name: alembic_version alembic_version_pkc; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.alembic_version
    ADD CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num);


--
-- Name: attachment attachment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attachment
    ADD CONSTRAINT attachment_pkey PRIMARY KEY (id);


--
-- Name: attachment attachment_unique_filename_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attachment
    ADD CONSTRAINT attachment_unique_filename_key UNIQUE (unique_filename);


--
-- Name: category category_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.category
    ADD CONSTRAINT category_name_key UNIQUE (name);


--
-- Name: category category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.category
    ADD CONSTRAINT category_pkey PRIMARY KEY (id);


--
-- Name: change_log_entry change_log_entry_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_log_entry
    ADD CONSTRAINT change_log_entry_pkey PRIMARY KEY (id);


--
-- Name: comment comment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comment
    ADD CONSTRAINT comment_pkey PRIMARY KEY (id);


--
-- Name: event_permission event_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_permission
    ADD CONSTRAINT event_permission_pkey PRIMARY KEY (id);


--
-- Name: event event_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event
    ADD CONSTRAINT event_pkey PRIMARY KEY (id);


--
-- Name: group group_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."group"
    ADD CONSTRAINT group_name_key UNIQUE (name);


--
-- Name: group group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."group"
    ADD CONSTRAINT group_pkey PRIMARY KEY (id);


--
-- Name: notification notification_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_pkey PRIMARY KEY (id);


--
-- Name: password_reset_token password_reset_token_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_token
    ADD CONSTRAINT password_reset_token_pkey PRIMARY KEY (id);


--
-- Name: password_reset_token password_reset_token_token_uuid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_token
    ADD CONSTRAINT password_reset_token_token_uuid_key UNIQUE (token_uuid);


--
-- Name: push_subscription push_subscription_endpoint_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.push_subscription
    ADD CONSTRAINT push_subscription_endpoint_key UNIQUE (endpoint);


--
-- Name: push_subscription push_subscription_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.push_subscription
    ADD CONSTRAINT push_subscription_pkey PRIMARY KEY (id);


--
-- Name: role role_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_name_key UNIQUE (name);


--
-- Name: role role_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.role
    ADD CONSTRAINT role_pkey PRIMARY KEY (id);


--
-- Name: status status_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.status
    ADD CONSTRAINT status_pkey PRIMARY KEY (id);


--
-- Name: task_assignment task_assignment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_assignment
    ADD CONSTRAINT task_assignment_pkey PRIMARY KEY (task_id, user_id);


--
-- Name: task_category task_category_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_category
    ADD CONSTRAINT task_category_name_key UNIQUE (name);


--
-- Name: task_category task_category_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_category
    ADD CONSTRAINT task_category_pkey PRIMARY KEY (id);


--
-- Name: task_history task_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_history
    ADD CONSTRAINT task_history_pkey PRIMARY KEY (id);


--
-- Name: task task_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT task_pkey PRIMARY KEY (id);


--
-- Name: user user_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_email_key UNIQUE (email);


--
-- Name: user_group user_group_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_group
    ADD CONSTRAINT user_group_pkey PRIMARY KEY (user_id, group_id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: user user_username_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_username_key UNIQUE (username);


--
-- Name: ix_push_subscription_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_push_subscription_timestamp ON public.push_subscription USING btree ("timestamp");


--
-- Name: attachment fk_attachment_task_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attachment
    ADD CONSTRAINT fk_attachment_task_id FOREIGN KEY (task_id) REFERENCES public.task(id);


--
-- Name: attachment fk_attachment_uploaded_by_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.attachment
    ADD CONSTRAINT fk_attachment_uploaded_by_user_id FOREIGN KEY (uploaded_by_user_id) REFERENCES public."user"(id);


--
-- Name: change_log_entry fk_changelog_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.change_log_entry
    ADD CONSTRAINT fk_changelog_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: comment fk_comment_task_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comment
    ADD CONSTRAINT fk_comment_task_id FOREIGN KEY (task_id) REFERENCES public.task(id);


--
-- Name: comment fk_comment_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comment
    ADD CONSTRAINT fk_comment_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: event fk_event_author_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event
    ADD CONSTRAINT fk_event_author_id FOREIGN KEY (author_id) REFERENCES public."user"(id);


--
-- Name: event fk_event_category_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event
    ADD CONSTRAINT fk_event_category_id FOREIGN KEY (category_id) REFERENCES public.category(id);


--
-- Name: event_permission fk_event_permission_event_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_permission
    ADD CONSTRAINT fk_event_permission_event_id FOREIGN KEY (event_id) REFERENCES public.event(id);


--
-- Name: event_permission fk_event_permission_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event_permission
    ADD CONSTRAINT fk_event_permission_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id) ON DELETE CASCADE;


--
-- Name: event fk_event_status_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.event
    ADD CONSTRAINT fk_event_status_id FOREIGN KEY (status_id) REFERENCES public.status(id);


--
-- Name: password_reset_token fk_password_reset_token_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_token
    ADD CONSTRAINT fk_password_reset_token_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: task_assignment fk_task_assignment_task_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_assignment
    ADD CONSTRAINT fk_task_assignment_task_id FOREIGN KEY (task_id) REFERENCES public.task(id);


--
-- Name: task_assignment fk_task_assignment_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_assignment
    ADD CONSTRAINT fk_task_assignment_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: task fk_task_completed_by_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT fk_task_completed_by_id FOREIGN KEY (completed_by_id) REFERENCES public."user"(id);


--
-- Name: task fk_task_event_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT fk_task_event_id FOREIGN KEY (event_id) REFERENCES public.event(id);


--
-- Name: task_history fk_task_history_task_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_history
    ADD CONSTRAINT fk_task_history_task_id FOREIGN KEY (task_id) REFERENCES public.task(id);


--
-- Name: task_history fk_task_history_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task_history
    ADD CONSTRAINT fk_task_history_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: task fk_task_status_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT fk_task_status_id FOREIGN KEY (task_status_id) REFERENCES public.status(id);


--
-- Name: task fk_task_task_category_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.task
    ADD CONSTRAINT fk_task_task_category_id FOREIGN KEY (task_category_id) REFERENCES public.task_category(id);


--
-- Name: user_group fk_user_group_group_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_group
    ADD CONSTRAINT fk_user_group_group_id FOREIGN KEY (group_id) REFERENCES public."group"(id);


--
-- Name: user_group fk_user_group_user_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_group
    ADD CONSTRAINT fk_user_group_user_id FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: user fk_user_role_id; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT fk_user_role_id FOREIGN KEY (role_id) REFERENCES public.role(id);


--
-- Name: notification notification_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.notification
    ADD CONSTRAINT notification_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: push_subscription push_subscription_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.push_subscription
    ADD CONSTRAINT push_subscription_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: DEFAULT PRIVILEGES FOR SEQUENCES; Type: DEFAULT ACL; Schema: -; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON SEQUENCES TO gerenciador_eventos_db_glqj_user;


--
-- Name: DEFAULT PRIVILEGES FOR TYPES; Type: DEFAULT ACL; Schema: -; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON TYPES TO gerenciador_eventos_db_glqj_user;


--
-- Name: DEFAULT PRIVILEGES FOR FUNCTIONS; Type: DEFAULT ACL; Schema: -; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON FUNCTIONS TO gerenciador_eventos_db_glqj_user;


--
-- Name: DEFAULT PRIVILEGES FOR TABLES; Type: DEFAULT ACL; Schema: -; Owner: -
--

ALTER DEFAULT PRIVILEGES FOR ROLE postgres GRANT ALL ON TABLES TO gerenciador_eventos_db_glqj_user;


--
-- PostgreSQL database dump complete
--

\unrestrict CD56chOgyAGmkI4qmwJLK6hm7qAEYsgw6c4giCkMaKC4YZhAI3AMX6RxgxKOaso

