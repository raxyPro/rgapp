-- 0006_social.sql
-- Social module posts (root + reply, optional image + CV link)

CREATE TABLE IF NOT EXISTS rb_social_post (
  post_id BIGINT NOT NULL AUTO_INCREMENT,
  user_id BIGINT NOT NULL,
  parent_id BIGINT NULL,
  body TEXT NOT NULL,
  image_path VARCHAR(500) NULL,
  cvfile_id BIGINT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (post_id),
  KEY ix_social_user (user_id),
  KEY ix_social_parent (parent_id),
  KEY ix_social_root (parent_id, created_at),
  KEY ix_social_cvfile (cvfile_id),
  CONSTRAINT fk_social_user FOREIGN KEY (user_id) REFERENCES rb_user(user_id) ON DELETE CASCADE,
  CONSTRAINT fk_social_parent FOREIGN KEY (parent_id) REFERENCES rb_social_post(post_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
