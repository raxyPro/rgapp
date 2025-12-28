-- 0012_cv_cover_letter_pdf.sql
-- Optional cover letter PDF stored per CV file

ALTER TABLE rb_cv_file
  ADD COLUMN cover_letter_path VARCHAR(500) NULL AFTER job_pref,
  ADD COLUMN cover_letter_name VARCHAR(255) NULL AFTER cover_letter_path,
  ADD COLUMN cover_letter_mime VARCHAR(100) NULL AFTER cover_letter_name,
  ADD COLUMN cover_letter_size BIGINT NULL AFTER cover_letter_mime;

