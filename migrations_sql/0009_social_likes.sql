-- 0009_social_likes.sql
-- Likes for social posts

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
