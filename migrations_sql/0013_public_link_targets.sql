-- 0013_public_link_targets.sql
-- Add share type and target fields to public links

ALTER TABLE rb_cv_public_link
  ADD COLUMN share_type ENUM('public','user','email') NOT NULL DEFAULT 'public' AFTER created_by,
  ADD COLUMN target VARCHAR(320) NULL AFTER share_type;

