CREATE TABLE `chat_topic` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(100) NOT NULL,
  `created_by` INT,  -- FK to vemp.ID
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_chat_topic_name` (`name`),
  FOREIGN KEY (`created_by`) REFERENCES `vemp`(`ID`) ON DELETE SET NULL
);

CREATE TABLE `chat_topic_user` (
  `topic_id` INT NOT NULL,
  `user_id` INT NOT NULL,
  `joined_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`topic_id`, `user_id`),
  FOREIGN KEY (`topic_id`) REFERENCES `chat_topic`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`user_id`) REFERENCES `vemp`(`ID`) ON DELETE CASCADE
);


CREATE TABLE `chat_message` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `topic_id` INT NOT NULL,
  `sender_id` INT NOT NULL,
  `message` TEXT NOT NULL,
  `sent_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  FOREIGN KEY (`topic_id`) REFERENCES `chat_topic`(`id`) ON DELETE CASCADE,
  FOREIGN KEY (`sender_id`) REFERENCES `vemp`(`ID`) ON DELETE CASCADE
);
