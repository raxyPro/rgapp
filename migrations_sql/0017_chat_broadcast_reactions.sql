-- 0017_chat_broadcast_reactions.sql
-- Adds broadcast chat support, reply references, and emoji reactions.

-- Expand chat thread types to include broadcast.
ALTER TABLE rb_chat_thread
  MODIFY COLUMN thread_type ENUM('dm','group','broadcast') NOT NULL DEFAULT 'dm';

-- Allow messages to reference another message (for replies) in an idempotent way.
SET @col := (SELECT COUNT(*) FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = 'rb_chat_message' AND column_name = 'reply_to_message_id');
SET @stmt := IF(@col = 0, 'ALTER TABLE rb_chat_message ADD COLUMN reply_to_message_id BIGINT NULL AFTER body', 'SELECT 1');
PREPARE s1 FROM @stmt; EXECUTE s1; DEALLOCATE PREPARE s1;

SET @idx := (SELECT COUNT(*) FROM information_schema.statistics WHERE table_schema = DATABASE() AND table_name = 'rb_chat_message' AND index_name = 'idx_chat_msg_reply_to');
SET @stmt := IF(@idx = 0, 'ALTER TABLE rb_chat_message ADD KEY idx_chat_msg_reply_to (reply_to_message_id)', 'SELECT 1');
PREPARE s2 FROM @stmt; EXECUTE s2; DEALLOCATE PREPARE s2;

SET @fk := (SELECT COUNT(*) FROM information_schema.table_constraints WHERE constraint_schema = DATABASE() AND table_name = 'rb_chat_message' AND constraint_name = 'fk_chat_msg_reply');
SET @stmt := IF(@fk = 0, 'ALTER TABLE rb_chat_message ADD CONSTRAINT fk_chat_msg_reply FOREIGN KEY (reply_to_message_id) REFERENCES rb_chat_message(message_id) ON DELETE SET NULL', 'SELECT 1');
PREPARE s3 FROM @stmt; EXECUTE s3; DEALLOCATE PREPARE s3;

-- Emoji reactions per message per user.
CREATE TABLE IF NOT EXISTS rb_chat_message_reaction (
  reaction_id BIGINT NOT NULL AUTO_INCREMENT,
  message_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  emoji VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (reaction_id),
  UNIQUE KEY uq_chat_message_reaction (message_id, user_id),
  KEY ix_chat_reaction_message (message_id),
  KEY ix_chat_reaction_user (user_id),
  CONSTRAINT fk_chat_reaction_message
    FOREIGN KEY (message_id) REFERENCES rb_chat_message(message_id) ON DELETE CASCADE,
  CONSTRAINT fk_chat_reaction_user
    FOREIGN KEY (user_id) REFERENCES rb_user(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
