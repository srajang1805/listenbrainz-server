CREATE TYPE background_tasks_status_type AS ENUM ('pending', 'running', 'failed');

BEGIN;

ALTER TABLE background_tasks ADD COLUMN status background_tasks_status_type NOT NULL DEFAULT 'pending';
ALTER TABLE background_tasks ADD COLUMN claimed_at TIMESTAMP WITH TIME ZONE;

COMMIT;
