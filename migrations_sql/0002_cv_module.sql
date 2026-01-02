-- 0002_cv_module.sql
-- CV module tables + module registration.
-- Safe to run multiple times.

INSERT INTO rb_module (module_key, name, description, is_enabled)
SELECT 'cv', 'CV', 'vCard + One-Page CV module', 1
WHERE NOT EXISTS (SELECT 1 FROM rb_module WHERE module_key='cv');

CREATE TABLE IF NOT EXISTS rb_cv_pair (
  cv_id BIGINT NOT NULL AUTO_INCREMENT,
  user_id BIGINT NOT NULL,

  v_name VARCHAR(120) NOT NULL DEFAULT '',
  v_company VARCHAR(120) NOT NULL DEFAULT '',
  v_email VARCHAR(120) NOT NULL DEFAULT '',
  v_phone VARCHAR(50) NOT NULL DEFAULT '',
  v_primary_skill VARCHAR(120) NOT NULL DEFAULT '',
  v_skill_description TEXT NOT NULL,
  v_organizations VARCHAR(255) NOT NULL DEFAULT '',
  v_achievements VARCHAR(255) NOT NULL DEFAULT '',

  onepage_html TEXT NOT NULL,

  is_archived BOOLEAN NOT NULL DEFAULT 0,

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

  PRIMARY KEY (cv_id),
  INDEX idx_cv_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_cv_share (
  share_id BIGINT NOT NULL AUTO_INCREMENT,
  cv_id BIGINT NOT NULL,
  owner_user_id BIGINT NOT NULL,

  target_user_id BIGINT NULL,
  target_email VARCHAR(200) NULL,

  share_token VARCHAR(64) NOT NULL,
  is_public BOOLEAN NOT NULL DEFAULT 0,
  is_archived BOOLEAN NOT NULL DEFAULT 0,

  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,

  PRIMARY KEY (share_id),
  UNIQUE KEY uk_share_token (share_token),
  INDEX idx_share_cv (cv_id),
  INDEX idx_share_owner (owner_user_id),
  INDEX idx_share_target_user (target_user_id),
  INDEX idx_share_target_email (target_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
