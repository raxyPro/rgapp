-- 0003_cv_onepage_editable.sql
-- Adds editable One-Page CV segments to rb_cv_pair
-- Safe to run once (tracked by rb_schema_migrations)

ALTER TABLE rb_cv_pair
  ADD COLUMN op_name VARCHAR(120) NOT NULL DEFAULT '' AFTER v_achievements,
  ADD COLUMN op_email VARCHAR(120) NOT NULL DEFAULT '' AFTER op_name,
  ADD COLUMN op_phone VARCHAR(50) NOT NULL DEFAULT '' AFTER op_email,
  ADD COLUMN op_title VARCHAR(150) NOT NULL DEFAULT '' AFTER op_phone,
  ADD COLUMN op_linkedin_url VARCHAR(255) NOT NULL DEFAULT '' AFTER op_title,
  ADD COLUMN op_website_url VARCHAR(255) NOT NULL DEFAULT '' AFTER op_linkedin_url,
  ADD COLUMN op_about TEXT NOT NULL AFTER op_website_url,
  ADD COLUMN op_skills TEXT NOT NULL AFTER op_about,
  ADD COLUMN op_experience TEXT NOT NULL AFTER op_skills,
  ADD COLUMN op_academic TEXT NOT NULL AFTER op_experience,
  ADD COLUMN op_achievements TEXT NOT NULL AFTER op_academic,
  ADD COLUMN op_final_remark TEXT NOT NULL AFTER op_achievements;
