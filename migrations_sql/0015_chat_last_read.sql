-- 0015_chat_last_read.sql
-- Add per-member last_read_at to support unread counts.

ALTER TABLE rb_chat_thread_member
  ADD COLUMN last_read_at DATETIME NULL AFTER joined_at;

-- Initialize last_read_at to now for existing memberships to avoid counting all history as unread.
UPDATE rb_chat_thread_member SET last_read_at = CURRENT_TIMESTAMP WHERE last_read_at IS NULL;
