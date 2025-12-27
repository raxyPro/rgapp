-- 0008_user_handle.sql
-- Add unique handle to user profile for privacy display

ALTER TABLE rb_user_profile
  ADD COLUMN handle VARCHAR(64) NULL UNIQUE AFTER user_id;

CREATE UNIQUE INDEX uq_rb_profile_handle ON rb_user_profile(handle);
