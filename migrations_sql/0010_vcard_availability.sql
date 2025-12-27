-- 0010_vcard_availability.sql
-- Extra availability fields on vCard

ALTER TABLE rb_vcard
  ADD COLUMN location VARCHAR(150) NULL AFTER tagline,
  ADD COLUMN work_mode VARCHAR(20) NULL AFTER location,
  ADD COLUMN city VARCHAR(120) NULL AFTER work_mode,
  ADD COLUMN available_from DATE NULL AFTER city,
  ADD COLUMN hours_per_day INT NULL AFTER available_from;

