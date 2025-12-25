08-Jul-25
next make chat work good
show topic on left, message on right 
ability send message
ability to reply message
on load show all messages since all undread message (from all topic)

improve cnts


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

for each users there are list of topic that he/she can participate

chat use cases
when user load chat application
all the topic that user participate goes to front end and topic is displayed

Prompt 07-Jul-25

great now build chat application 

when a user loads the chat first time , all teh chats are loaded and sent to HTML 
all the topic and messages will be displayed in one window

so give me a flask route code consider there is flask sqlalchmey defition as Vemp, ChatTopic,ChatTopicUser,ChatMessage

also give me a html (div only ) to load and display the chats in div. each topic is displayed as card in dev and once a user press on the card the chat is active and user can post a new message

