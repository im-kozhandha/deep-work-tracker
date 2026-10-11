-- Sample data for the Deep Work Session Tracker.
-- Prerequisite: `alembic upgrade head` has been run (needs interruptions.resume_time).
-- All timestamps are UTC in 'YYYY-MM-DD HH:MM:SS' format and relative to "now", so the
-- active/paused samples look current and the history charts have recent data.
-- Sessions are matched by title, never by id. The script is safe to run repeatedly.
-- Note: the paused sample is abandoned automatically about 25 minutes after loading,
-- which is the documented 30-minute abandonment rule at work.

BEGIN TRANSACTION;

DELETE FROM interruptions
WHERE session_id IN (SELECT id FROM sessions WHERE title LIKE 'Seed: %');
DELETE FROM sessions WHERE title LIKE 'Seed: %';

-- 1. scheduled: not started yet.
INSERT INTO sessions (title, goal, scheduled_duration, status, created_at)
VALUES ('Seed: Plan sprint', 'Outline next sprint tasks', 25, 'scheduled',
        datetime('now', '-1 hours'));

-- 2. active: started 10 minutes ago.
INSERT INTO sessions (title, goal, scheduled_duration, start_time, status, created_at)
VALUES ('Seed: Write report', 'Draft the introduction and methods', 50,
        datetime('now', '-10 minutes'), 'active', datetime('now', '-15 minutes'));

-- 3. completed within the limit, with one resumed pause (30 min elapsed of 30 scheduled).
INSERT INTO sessions (title, goal, scheduled_duration, start_time, end_time, status, created_at)
VALUES ('Seed: Code review', 'Review the open pull requests', 30,
        datetime('now', '-1 day', '-3 hours'),
        datetime('now', '-1 day', '-3 hours', '+30 minutes'),
        'completed',
        datetime('now', '-1 day', '-3 hours', '-5 minutes'));
INSERT INTO interruptions (session_id, reason, pause_time, resume_time)
SELECT id, 'Quick question from a teammate',
       datetime('now', '-1 day', '-3 hours', '+10 minutes'),
       datetime('now', '-1 day', '-3 hours', '+15 minutes')
FROM sessions WHERE title = 'Seed: Code review';

-- 4. completed without any interruption.
INSERT INTO sessions (title, goal, scheduled_duration, start_time, end_time, status, created_at)
VALUES ('Seed: Morning focus', 'Read two chapters', 25,
        datetime('now', '-2 days', '-5 hours'),
        datetime('now', '-2 days', '-5 hours', '+25 minutes'),
        'completed',
        datetime('now', '-2 days', '-5 hours', '-5 minutes'));

-- 5. paused 5 minutes ago with a recorded reason (still resumable).
INSERT INTO sessions (title, goal, scheduled_duration, start_time, status, created_at)
VALUES ('Seed: Research paper', 'Summarize three papers', 60,
        datetime('now', '-20 minutes'), 'paused', datetime('now', '-25 minutes'));
INSERT INTO interruptions (session_id, reason, pause_time, resume_time)
SELECT id, 'Phone call', datetime('now', '-5 minutes'), NULL
FROM sessions WHERE title = 'Seed: Research paper';

-- 6. interrupted: four pauses; the fourth is unresumed and ends the session at its pause time.
INSERT INTO sessions (title, goal, scheduled_duration, start_time, end_time, status, created_at)
VALUES ('Seed: Deep refactor', 'Split the billing module', 40,
        datetime('now', '-3 days', '-4 hours'),
        datetime('now', '-3 days', '-4 hours', '+28 minutes'),
        'interrupted',
        datetime('now', '-3 days', '-4 hours', '-5 minutes'));
INSERT INTO interruptions (session_id, reason, pause_time, resume_time)
SELECT id, 'Slack message',
       datetime('now', '-3 days', '-4 hours', '+5 minutes'),
       datetime('now', '-3 days', '-4 hours', '+8 minutes')
FROM sessions WHERE title = 'Seed: Deep refactor';
INSERT INTO interruptions (session_id, reason, pause_time, resume_time)
SELECT id, 'Meeting reminder',
       datetime('now', '-3 days', '-4 hours', '+12 minutes'),
       datetime('now', '-3 days', '-4 hours', '+15 minutes')
FROM sessions WHERE title = 'Seed: Deep refactor';
INSERT INTO interruptions (session_id, reason, pause_time, resume_time)
SELECT id, 'Snack break',
       datetime('now', '-3 days', '-4 hours', '+20 minutes'),
       datetime('now', '-3 days', '-4 hours', '+24 minutes')
FROM sessions WHERE title = 'Seed: Deep refactor';
INSERT INTO interruptions (session_id, reason, pause_time, resume_time)
SELECT id, 'Noisy construction outside',
       datetime('now', '-3 days', '-4 hours', '+28 minutes'),
       NULL
FROM sessions WHERE title = 'Seed: Deep refactor';

-- 7. overdue: 60 minutes elapsed of 50 scheduled (limit is 55), pauses included.
INSERT INTO sessions (title, goal, scheduled_duration, start_time, end_time, status, created_at)
VALUES ('Seed: Long workshop', 'Prepare the team workshop slides', 50,
        datetime('now', '-4 days', '-6 hours'),
        datetime('now', '-4 days', '-6 hours', '+60 minutes'),
        'overdue',
        datetime('now', '-4 days', '-6 hours', '-5 minutes'));
INSERT INTO interruptions (session_id, reason, pause_time, resume_time)
SELECT id, 'Colleague question',
       datetime('now', '-4 days', '-6 hours', '+20 minutes'),
       datetime('now', '-4 days', '-6 hours', '+30 minutes')
FROM sessions WHERE title = 'Seed: Long workshop';

-- 8. abandoned: paused and never resumed; ended 30 minutes after the pause (the timeout).
INSERT INTO sessions (title, goal, scheduled_duration, start_time, end_time, status, created_at)
VALUES ('Seed: Reading block', 'Finish the design book chapter', 45,
        datetime('now', '-5 days', '-2 hours'),
        datetime('now', '-5 days', '-2 hours', '+50 minutes'),
        'abandoned',
        datetime('now', '-5 days', '-2 hours', '-5 minutes'));
INSERT INTO interruptions (session_id, reason, pause_time, resume_time)
SELECT id, 'Lunch',
       datetime('now', '-5 days', '-2 hours', '+20 minutes'),
       NULL
FROM sessions WHERE title = 'Seed: Reading block';

COMMIT;