-- 0017_feedback.sql
-- Feedback capture for admin review
CREATE TABLE IF NOT EXISTS rb_feedback (
  feedback_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  user_id BIGINT NOT NULL,
  body TEXT NOT NULL,
  meta JSON NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  KEY ix_feedback_user (user_id),
  KEY ix_feedback_created (created_at),
  CONSTRAINT fk_feedback_user FOREIGN KEY (user_id) REFERENCES rb_user(user_id) ON DELETE CASCADE
);
