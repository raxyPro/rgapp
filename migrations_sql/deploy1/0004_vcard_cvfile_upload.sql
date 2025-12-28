-- 0004_vcard_cvfile_upload.sql
-- vCard + CV Upload (PDF) module schema
-- No Alembic; tracked by rb_schema_migrations

CREATE TABLE IF NOT EXISTS rb_vcard (
  vcard_id BIGINT NOT NULL AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  name VARCHAR(150) NOT NULL DEFAULT '',
  email VARCHAR(150) NOT NULL DEFAULT '',
  phone VARCHAR(60) NOT NULL DEFAULT '',
  linkedin_url VARCHAR(255) NOT NULL DEFAULT '',
  tagline VARCHAR(255) NOT NULL DEFAULT '',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (vcard_id),
  UNIQUE KEY uq_rb_vcard_user (user_id),
  KEY idx_rb_vcard_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_vcard_item (
  item_id BIGINT NOT NULL AUTO_INCREMENT,
  vcard_id BIGINT NOT NULL,
  item_type VARCHAR(20) NOT NULL,
  title VARCHAR(150) NOT NULL DEFAULT '',
  description TEXT NOT NULL,
  experience TEXT NOT NULL,
  sort_order INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (item_id),
  KEY idx_rb_vcard_item_vcard (vcard_id),
  KEY idx_rb_vcard_item_type (item_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_cv_file (
  cvfile_id BIGINT NOT NULL AUTO_INCREMENT,
  owner_user_id BIGINT NOT NULL,
  cv_name VARCHAR(200) NOT NULL DEFAULT '',
  original_filename VARCHAR(255) NOT NULL DEFAULT '',
  stored_path VARCHAR(500) NOT NULL DEFAULT '',
  mime_type VARCHAR(100) NOT NULL DEFAULT 'application/pdf',
  size_bytes BIGINT NOT NULL DEFAULT 0,
  is_archived TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (cvfile_id),
  KEY idx_rb_cv_file_owner (owner_user_id),
  KEY idx_rb_cv_file_arch (is_archived)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_vcard_share (
  share_id BIGINT NOT NULL AUTO_INCREMENT,
  vcard_id BIGINT NOT NULL,
  owner_user_id BIGINT NOT NULL,
  target_user_id BIGINT NULL,
  target_email VARCHAR(200) NULL,
  share_token VARCHAR(64) NOT NULL,
  is_public TINYINT(1) NOT NULL DEFAULT 0,
  is_archived TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (share_id),
  UNIQUE KEY uq_rb_vcard_share_token (share_token),
  KEY idx_rb_vcard_share_vcard (vcard_id),
  KEY idx_rb_vcard_share_owner (owner_user_id),
  KEY idx_rb_vcard_share_target_user (target_user_id),
  KEY idx_rb_vcard_share_target_email (target_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_cvfile_share (
  share_id BIGINT NOT NULL AUTO_INCREMENT,
  cvfile_id BIGINT NOT NULL,
  owner_user_id BIGINT NOT NULL,
  target_user_id BIGINT NULL,
  target_email VARCHAR(200) NULL,
  share_token VARCHAR(64) NOT NULL,
  is_public TINYINT(1) NOT NULL DEFAULT 0,
  is_archived TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (share_id),
  UNIQUE KEY uq_rb_cvfile_share_token (share_token),
  KEY idx_rb_cvfile_share_cvfile (cvfile_id),
  KEY idx_rb_cvfile_share_owner (owner_user_id),
  KEY idx_rb_cvfile_share_target_user (target_user_id),
  KEY idx_rb_cvfile_share_target_email (target_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
