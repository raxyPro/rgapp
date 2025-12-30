-- deploy1 (baseline/ship) full schema
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- Core
CREATE TABLE IF NOT EXISTS alembic_version (
  version_num VARCHAR(32) NOT NULL,
  PRIMARY KEY (version_num)
);

CREATE TABLE IF NOT EXISTS rb_user (
  user_id BIGINT NOT NULL AUTO_INCREMENT,
  email VARCHAR(320) NOT NULL,
  password_hash VARCHAR(255) DEFAULT NULL,
  status ENUM('invited','active','blocked','deleted') NOT NULL DEFAULT 'invited',
  is_admin TINYINT(1) NOT NULL DEFAULT 0,
  invited_at DATETIME DEFAULT NULL,
  invited_by BIGINT DEFAULT NULL,
  registered_at DATETIME DEFAULT NULL,
  last_login_at DATETIME DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  UNIQUE KEY uq_rb_user_email (email),
  KEY ix_rb_user_email (email),
  KEY ix_rb_user_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_module (
  module_key VARCHAR(50) NOT NULL,
  name VARCHAR(120) NOT NULL,
  description VARCHAR(255) DEFAULT NULL,
  is_enabled TINYINT(1) NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (module_key)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_user_module (
  user_id BIGINT NOT NULL,
  module_key VARCHAR(50) NOT NULL,
  has_access TINYINT(1) NOT NULL DEFAULT 1,
  granted_by BIGINT DEFAULT NULL,
  granted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id, module_key),
  KEY fk_um_module (module_key),
  CONSTRAINT fk_um_module FOREIGN KEY (module_key) REFERENCES rb_module(module_key) ON DELETE CASCADE,
  CONSTRAINT fk_um_user FOREIGN KEY (user_id) REFERENCES rb_user(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_user_profile (
  user_id BIGINT NOT NULL,
  handle VARCHAR(64) DEFAULT NULL,
  rgDisplay VARCHAR(200) NOT NULL,
  full_name VARCHAR(200) DEFAULT NULL,
  display_name VARCHAR(120) DEFAULT NULL,
  rgData JSON DEFAULT NULL,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (user_id),
  UNIQUE KEY uq_rb_profile_handle (handle),
  CONSTRAINT fk_profile_user FOREIGN KEY (user_id) REFERENCES rb_user(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_schema_migrations (
  filename VARCHAR(255) NOT NULL,
  applied_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (filename)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_audit (
  audit_id BIGINT NOT NULL AUTO_INCREMENT,
  event_id VARCHAR(36) NOT NULL,
  tblname VARCHAR(64) NOT NULL,
  row_id BIGINT NOT NULL,
  audit_date DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  action ENUM('add','invite','register','login','edit','grant_module','revoke_module') NOT NULL,
  actor_id BIGINT DEFAULT NULL,
  source ENUM('self','admin','api') NOT NULL DEFAULT 'api',
  prev_data JSON DEFAULT NULL,
  new_data JSON DEFAULT NULL,
  PRIMARY KEY (audit_id),
  KEY ix_rb_audit_event_id (event_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_invitation (
  invitation_id BIGINT NOT NULL AUTO_INCREMENT,
  email VARCHAR(320) NOT NULL,
  token VARCHAR(255) NOT NULL,
  expires_at DATETIME NOT NULL,
  used TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (invitation_id),
  UNIQUE KEY uq_invite_token (token),
  KEY ix_invite_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_password_reset (
  reset_id BIGINT NOT NULL AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  token VARCHAR(255) NOT NULL,
  expires_at DATETIME NOT NULL,
  used TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (reset_id),
  UNIQUE KEY uq_reset_token (token),
  KEY fk_reset_user (user_id),
  CONSTRAINT fk_reset_user FOREIGN KEY (user_id) REFERENCES rb_user(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Chat
CREATE TABLE IF NOT EXISTS rb_chat_thread (
  thread_id BIGINT NOT NULL AUTO_INCREMENT,
  thread_type ENUM('dm','group') NOT NULL DEFAULT 'dm',
  name VARCHAR(120) DEFAULT NULL,
  created_by BIGINT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (thread_id),
  KEY ix_chat_thread_type (thread_type),
  KEY ix_chat_thread_updated (updated_at),
  KEY fk_chat_thread_created_by (created_by),
  CONSTRAINT fk_chat_thread_created_by FOREIGN KEY (created_by) REFERENCES rb_user(user_id) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_chat_thread_member (
  id BIGINT NOT NULL AUTO_INCREMENT,
  thread_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  role ENUM('owner','member') NOT NULL DEFAULT 'member',
  joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  last_read_at DATETIME DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_chat_thread_member (thread_id, user_id),
  KEY ix_chat_member_user (user_id),
  KEY ix_chat_member_thread (thread_id),
  CONSTRAINT fk_chat_member_thread FOREIGN KEY (thread_id) REFERENCES rb_chat_thread(thread_id) ON DELETE CASCADE,
  CONSTRAINT fk_chat_member_user FOREIGN KEY (user_id) REFERENCES rb_user(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_chat_message (
  message_id BIGINT NOT NULL AUTO_INCREMENT,
  thread_id BIGINT NOT NULL,
  sender_id BIGINT NOT NULL,
  body TEXT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (message_id),
  KEY ix_chat_msg_thread_created (thread_id, created_at),
  KEY ix_chat_msg_sender (sender_id),
  CONSTRAINT fk_chat_msg_sender FOREIGN KEY (sender_id) REFERENCES rb_user(user_id) ON DELETE RESTRICT,
  CONSTRAINT fk_chat_msg_thread FOREIGN KEY (thread_id) REFERENCES rb_chat_thread(thread_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Unified CV/vCard
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

CREATE TABLE IF NOT EXISTS rb_cv_public_link (
  link_id BIGINT NOT NULL AUTO_INCREMENT,
  cvfile_id BIGINT NOT NULL,
  created_by BIGINT NOT NULL,
  share_type ENUM('public','user','email') NOT NULL DEFAULT 'public',
  target VARCHAR(320) DEFAULT NULL,
  name VARCHAR(150) DEFAULT NULL,
  token VARCHAR(64) NOT NULL,
  allow_download TINYINT(1) NOT NULL DEFAULT 0,
  password_hash VARCHAR(255) DEFAULT NULL,
  status ENUM('active','disabled') NOT NULL DEFAULT 'active',
  expires_at DATETIME DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (link_id),
  UNIQUE KEY uq_cv_public_token (token),
  KEY idx_cv_public_cv (cvfile_id),
  KEY idx_cv_public_creator (created_by),
  CONSTRAINT fk_cv_public_profile FOREIGN KEY (cvfile_id) REFERENCES rb_cv_profile(profile_id) ON DELETE CASCADE,
  CONSTRAINT fk_cv_public_creator FOREIGN KEY (created_by) REFERENCES rb_user(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_cvfile_share (
  share_id BIGINT NOT NULL AUTO_INCREMENT,
  cvfile_id BIGINT NOT NULL,
  owner_user_id BIGINT NOT NULL,
  target_user_id BIGINT DEFAULT NULL,
  target_email VARCHAR(200) DEFAULT NULL,
  share_token VARCHAR(64) NOT NULL,
  is_public TINYINT(1) NOT NULL DEFAULT 0,
  is_archived TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (share_id),
  UNIQUE KEY uq_rb_cvfile_share_token (share_token),
  KEY idx_rb_cvfile_share_cvfile (cvfile_id),
  KEY idx_rb_cvfile_share_owner (owner_user_id),
  KEY idx_rb_cvfile_share_target_user (target_user_id),
  KEY idx_rb_cvfile_share_target_email (target_email),
  CONSTRAINT fk_cvfile_share_profile FOREIGN KEY (cvfile_id) REFERENCES rb_cv_profile(profile_id) ON DELETE CASCADE,
  CONSTRAINT fk_cvfile_share_owner FOREIGN KEY (owner_user_id) REFERENCES rb_user(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_vcard_share (
  share_id BIGINT NOT NULL AUTO_INCREMENT,
  vcard_id BIGINT NOT NULL,
  owner_user_id BIGINT NOT NULL,
  target_user_id BIGINT DEFAULT NULL,
  target_email VARCHAR(200) DEFAULT NULL,
  share_token VARCHAR(64) NOT NULL,
  is_public TINYINT(1) NOT NULL DEFAULT 0,
  is_archived TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (share_id),
  UNIQUE KEY uq_rb_vcard_share_token (share_token),
  KEY idx_rb_vcard_share_vcard (vcard_id),
  KEY idx_rb_vcard_share_owner (owner_user_id),
  KEY idx_rb_vcard_share_target_user (target_user_id),
  KEY idx_rb_vcard_share_target_email (target_email),
  CONSTRAINT fk_vcard_share_profile FOREIGN KEY (vcard_id) REFERENCES rb_cv_profile(profile_id) ON DELETE CASCADE,
  CONSTRAINT fk_vcard_share_owner FOREIGN KEY (owner_user_id) REFERENCES rb_user(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- One-page CV builder (unchanged)
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
  op_name VARCHAR(120) NOT NULL DEFAULT '',
  op_email VARCHAR(120) NOT NULL DEFAULT '',
  op_phone VARCHAR(50) NOT NULL DEFAULT '',
  op_title VARCHAR(150) NOT NULL DEFAULT '',
  op_linkedin_url VARCHAR(255) NOT NULL DEFAULT '',
  op_website_url VARCHAR(255) NOT NULL DEFAULT '',
  op_about TEXT NOT NULL,
  op_skills TEXT NOT NULL,
  op_experience TEXT NOT NULL,
  op_academic TEXT NOT NULL,
  op_achievements TEXT NOT NULL,
  op_final_remark TEXT NOT NULL,
  onepage_html TEXT NOT NULL,
  is_archived TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (cv_id),
  KEY idx_cv_user (user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_cv_share (
  share_id BIGINT NOT NULL AUTO_INCREMENT,
  cv_id BIGINT NOT NULL,
  owner_user_id BIGINT NOT NULL,
  target_user_id BIGINT DEFAULT NULL,
  target_email VARCHAR(200) DEFAULT NULL,
  share_token VARCHAR(64) NOT NULL,
  is_public TINYINT(1) NOT NULL DEFAULT 0,
  is_archived TINYINT(1) NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (share_id),
  UNIQUE KEY uk_share_token (share_token),
  KEY idx_share_cv (cv_id),
  KEY idx_share_owner (owner_user_id),
  KEY idx_share_target_user (target_user_id),
  KEY idx_share_target_email (target_email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Social
CREATE TABLE IF NOT EXISTS rb_social_post (
  post_id BIGINT NOT NULL AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  parent_id BIGINT DEFAULT NULL,
  body TEXT NOT NULL,
  image_path VARCHAR(500) DEFAULT NULL,
  cvfile_id BIGINT DEFAULT NULL, -- stores rb_cv_profile.profile_id
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (post_id),
  KEY ix_social_user (user_id),
  KEY ix_social_parent (parent_id),
  KEY ix_social_root (parent_id, created_at),
  KEY ix_social_cvfile (cvfile_id),
  CONSTRAINT fk_social_parent FOREIGN KEY (parent_id) REFERENCES rb_social_post(post_id) ON DELETE CASCADE,
  CONSTRAINT fk_social_user FOREIGN KEY (user_id) REFERENCES rb_user(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_social_cvfile FOREIGN KEY (cvfile_id) REFERENCES rb_cv_profile(profile_id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_social_like (
  like_id BIGINT NOT NULL AUTO_INCREMENT,
  post_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (like_id),
  UNIQUE KEY uq_social_like (post_id, user_id),
  KEY idx_social_like_post (post_id),
  KEY idx_social_like_user (user_id),
  CONSTRAINT fk_social_like_post FOREIGN KEY (post_id) REFERENCES rb_social_post(post_id) ON DELETE CASCADE,
  CONSTRAINT fk_social_like_user FOREIGN KEY (user_id) REFERENCES rb_user(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

SET FOREIGN_KEY_CHECKS = 1;
