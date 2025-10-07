DEBUG: Itsdangerous version being used: 2.2.0
DEBUG: SQLALCHEMY_DATABASE_URI sendo usada: postgresql://gerenciador_eventos_db_glqj_user:jyiKbXIvOPGtIPzkraESYpUddW38ElKn@dpg-d39hdd7diees73f30ivg-a.virginia-postgres.render.com/gerenciador_eventos_db_glqj
DEBUG MAIL_SERVER: smtp.gmail.com
DEBUG MAIL_PORT: 587
DEBUG MAIL_USE_TLS: True
DEBUG MAIL_USERNAME (primeiras 3 letras): ger
DEBUG MAIL_PASSWORD (primeiras 3 letras): lrj
DEBUG MAIL_DEFAULT_SENDER: gerenciador.eventos@grandetemplo.com.br
BEGIN;

-- Running upgrade f54bc5e16af3 -> 9047c53290de

DEBUG: Dropped CHECK constraint '_user_or_group_check'.
DEBUG: Dropped foreign key 'fk_event_permission_group_id'.
DEBUG: Dropped foreign key 'fk_event_permission_role_id'.
DEBUG: Dropped index '_event_group_unique_idx'.
DEBUG: Dropped index '_event_user_unique_idx'.
DEBUG: Dropped column 'group_id'.
DEBUG: Dropped column 'role_id'.
DEBUG: Altered column 'user_id' to NOT NULL.
DEBUG: Created unique constraint '_event_user_unique_uc'.
ALTER TABLE event_permission DROP CONSTRAINT _user_or_group_check;

ALTER TABLE event_permission DROP CONSTRAINT fk_event_permission_group_id;

ALTER TABLE event_permission DROP CONSTRAINT fk_event_permission_role_id;

DROP INDEX _event_group_unique_idx;

DROP INDEX _event_user_unique_idx;

ALTER TABLE event_permission DROP COLUMN group_id;

ALTER TABLE event_permission DROP COLUMN role_id;

ALTER TABLE event_permission ALTER COLUMN user_id SET NOT NULL;

ALTER TABLE event_permission ADD CONSTRAINT _event_user_unique_uc UNIQUE (event_id, user_id);

UPDATE alembic_version SET version_num='9047c53290de' WHERE alembic_version.version_num = 'f54bc5e16af3';

COMMIT;

