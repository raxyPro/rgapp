-- 0007_public_links.sql
-- Multi public links for CV files with optional password and expiry

CREATE TABLE IF NOT EXISTS rb_cv_public_link (
  link_id BIGINT NOT NULL AUTO_INCREMENT,
  cvfile_id BIGINT NOT NULL,
  created_by BIGINT NOT NULL,
  name VARCHAR(150) NULL,
  token VARCHAR(64) NOT NULL,
  allow_download TINYINT(1) NOT NULL DEFAULT 0,
  password_hash VARCHAR(255) NULL,
  status ENUM('active','disabled') NOT NULL DEFAULT 'active',
  expires_at DATETIME NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (link_id),
  UNIQUE KEY uq_cv_public_token (token),
  KEY idx_cv_public_cv (cvfile_id),
  KEY idx_cv_public_creator (created_by),
  CONSTRAINT fk_cv_public_cv FOREIGN KEY (cvfile_id) REFERENCES rb_cv_file(cvfile_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
