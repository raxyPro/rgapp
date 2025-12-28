-- 0011_cv_preferences.sql
-- Cover letter and job preference per CV file

ALTER TABLE rb_cv_file
  ADD COLUMN cover_letter TEXT NULL AFTER cv_name,
  ADD COLUMN job_pref TEXT NULL AFTER cover_letter;

