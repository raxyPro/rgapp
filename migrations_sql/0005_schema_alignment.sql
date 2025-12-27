-- 0005_schema_alignment.sql
-- Align schema with latest data dictionary:
-- - Ensure rb_audit enum supports grant/revoke module events
-- - Add invitation/password reset tables if missing
-- - Create chat tables with documented indexes
-- - Add missing chat indexes when tables already exist

-- Extend rb_audit.action enum to include grant/revoke module events
ALTER TABLE rb_audit
  MODIFY action ENUM('add','invite','register','login','edit','grant_module','revoke_module') NOT NULL;

-- Invitations (token store)
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

-- Password reset (token store)
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

-- Chat tables
CREATE TABLE IF NOT EXISTS rb_chat_thread (
  thread_id BIGINT NOT NULL AUTO_INCREMENT,
  thread_type ENUM('dm','group') NOT NULL DEFAULT 'dm',
  name VARCHAR(120) NULL,
  created_by BIGINT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (thread_id),
  KEY ix_chat_thread_type (thread_type),
  KEY ix_chat_thread_updated (updated_at),
  KEY fk_chat_thread_created_by (created_by),
  CONSTRAINT fk_chat_thread_created_by FOREIGN KEY (created_by) REFERENCES rb_user(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS rb_chat_thread_member (
  id BIGINT NOT NULL AUTO_INCREMENT,
  thread_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  role ENUM('owner','member') NOT NULL DEFAULT 'member',
  joined_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_chat_thread_member (thread_id, user_id),
  KEY ix_chat_member_user (user_id),
  KEY ix_chat_member_thread (thread_id),
  CONSTRAINT fk_chat_thread_member_thread FOREIGN KEY (thread_id) REFERENCES rb_chat_thread(thread_id) ON DELETE CASCADE,
  CONSTRAINT fk_chat_thread_member_user FOREIGN KEY (user_id) REFERENCES rb_user(user_id)
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
  CONSTRAINT fk_chat_msg_thread FOREIGN KEY (thread_id) REFERENCES rb_chat_thread(thread_id) ON DELETE CASCADE,
  CONSTRAINT fk_chat_msg_sender FOREIGN KEY (sender_id) REFERENCES rb_user(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Add missing chat indexes when tables already exist
ALTER TABLE rb_chat_thread
  ADD INDEX ix_chat_thread_type (thread_type),
  ADD INDEX ix_chat_thread_updated (updated_at),
  ADD INDEX fk_chat_thread_created_by (created_by);

ALTER TABLE rb_chat_thread_member
  ADD INDEX ix_chat_member_thread (thread_id);

ALTER TABLE rb_chat_message
  ADD INDEX ix_chat_msg_sender (sender_id);
