-- 0016_cv_unified_profile.sql
-- Single-table storage for vCard + CV (JSON details + binary PDF)
-- No Alembic; tracked by rb_schema_migrations

-- Drop and recreate unified profile table to ensure a clean definition
SET @prev_fk_checks := @@FOREIGN_KEY_CHECKS;
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS rb_cv_profile;
SET FOREIGN_KEY_CHECKS = @prev_fk_checks;

CREATE TABLE IF NOT EXISTS rb_cv_profile (
  profile_id BIGINT NOT NULL AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  doc_type VARCHAR(20) NOT NULL, -- 'vcard' or 'cv'
  details JSON NOT NULL,
  pdf_data LONGBLOB NULL,
  pdf_name VARCHAR(255) NULL,
  pdf_mime VARCHAR(120) NULL,
  pdf_size BIGINT NULL,
  cover_pdf_data LONGBLOB NULL,
  cover_pdf_name VARCHAR(255) NULL,
  cover_pdf_mime VARCHAR(120) NULL,
  cover_pdf_size BIGINT NULL,
  is_archived TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (profile_id),
  KEY idx_cv_profile_user (user_id),
  KEY idx_cv_profile_user_type (user_id, doc_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Backfill existing vCards into unified table (keep original IDs to preserve shares)
INSERT IGNORE INTO rb_cv_profile (profile_id, user_id, doc_type, details, is_archived, created_at, updated_at)
SELECT
  v.vcard_id AS profile_id,
  v.user_id,
  'vcard' AS doc_type,
  JSON_OBJECT(
    'name', v.name,
    'email', v.email,
    'phone', v.phone,
    'linkedin_url', v.linkedin_url,
    'tagline', v.tagline,
    'location', v.location,
    'work_mode', v.work_mode,
    'city', v.city,
    'available_from', v.available_from,
    'hours_per_day', v.hours_per_day,
    'skills', COALESCE(si.skills, JSON_ARRAY()),
    'services', COALESCE(se.services, JSON_ARRAY())
  ) AS details,
  0 AS is_archived,
  v.created_at,
  v.updated_at
FROM rb_vcard v
LEFT JOIN (
  SELECT vcard_id, JSON_ARRAYAGG(JSON_OBJECT(
    'item_type', item_type,
    'title', title,
    'description', description,
    'experience', experience,
    'sort_order', sort_order
  )) AS skills
  FROM rb_vcard_item
  WHERE item_type = 'skill'
  GROUP BY vcard_id
) si ON si.vcard_id = v.vcard_id
LEFT JOIN (
  SELECT vcard_id, JSON_ARRAYAGG(JSON_OBJECT(
    'item_type', item_type,
    'title', title,
    'description', description,
    'experience', experience,
    'sort_order', sort_order
  )) AS services
  FROM rb_vcard_item
  WHERE item_type = 'service'
  GROUP BY vcard_id
) se ON se.vcard_id = v.vcard_id;

-- Backfill existing CV files with an offset to avoid ID collisions with vCards
SET @cv_offset := 1000000000;

INSERT IGNORE INTO rb_cv_profile (profile_id, user_id, doc_type, details, pdf_name, pdf_mime, pdf_size, is_archived, created_at, updated_at)
SELECT
  cv.cvfile_id + @cv_offset AS profile_id,
  cv.owner_user_id AS user_id,
  'cv' AS doc_type,
  JSON_OBJECT(
    'cv_name', cv.cv_name,
    'cover_letter', cv.cover_letter,
    'job_pref', cv.job_pref,
    'original_filename', cv.original_filename,
    'cover_letter_name', cv.cover_letter_name,
    'cover_letter_mime', cv.cover_letter_mime,
    'cover_letter_size', cv.cover_letter_size
  ) AS details,
  cv.original_filename AS pdf_name,
  cv.mime_type AS pdf_mime,
  cv.size_bytes AS pdf_size,
  cv.is_archived,
  cv.created_at,
  cv.updated_at
FROM rb_cv_file cv;

-- Update references to point to the new profile IDs for CVs
UPDATE rb_cv_public_link SET cvfile_id = cvfile_id + @cv_offset WHERE cvfile_id IS NOT NULL;
UPDATE rb_cvfile_share SET cvfile_id = cvfile_id + @cv_offset WHERE cvfile_id IS NOT NULL;

-- Optional table: social_post (skip if not present)
SET @has_social := (
  SELECT COUNT(*)
  FROM information_schema.TABLES
  WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'social_post'
);
SET @sql_social := IF(@has_social > 0, 'UPDATE social_post SET cvfile_id = cvfile_id + @cv_offset WHERE cvfile_id IS NOT NULL', 'SELECT 1');
PREPARE stmt_soc FROM @sql_social;
EXECUTE stmt_soc;
DEALLOCATE PREPARE stmt_soc;

-- Ensure AUTO_INCREMENT is higher than any inserted ID
SET @max_profile := (SELECT IFNULL(MAX(profile_id), 0) FROM rb_cv_profile);
SET @sql_ai := CONCAT('ALTER TABLE rb_cv_profile AUTO_INCREMENT = ', @max_profile + 1);
PREPARE stmt_ai FROM @sql_ai;
EXECUTE stmt_ai;
DEALLOCATE PREPARE stmt_ai;

-- Re-point public links FK to the unified table
SET @fk := (
  SELECT CONSTRAINT_NAME
  FROM information_schema.REFERENTIAL_CONSTRAINTS
  WHERE CONSTRAINT_SCHEMA = DATABASE()
    AND CONSTRAINT_NAME = 'fk_cv_public_cv'
    AND TABLE_NAME = 'rb_cv_public_link'
);
SET @sql := IF(@fk IS NOT NULL, 'ALTER TABLE rb_cv_public_link DROP FOREIGN KEY fk_cv_public_cv', 'SELECT 1');
PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- Cleanup any public links that reference missing profiles before enforcing FK
DELETE FROM rb_cv_public_link WHERE cvfile_id NOT IN (SELECT profile_id FROM rb_cv_profile);

ALTER TABLE rb_cv_public_link
  ADD CONSTRAINT fk_cv_public_profile FOREIGN KEY (cvfile_id) REFERENCES rb_cv_profile(profile_id) ON DELETE CASCADE;
