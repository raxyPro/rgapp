my_flask_app/
├── __init__.py         # Application factory, main app setup, db init
├── models.py           # SQLAlchemy models (User, Task)
├── auth/               # Blueprint for authentication features
│   ├── __init__.py     # Auth Blueprint definition
│   └── routes.py       # Auth routes (login, logout, forgot_pin, set_pin)
├── tasks/              # Blueprint for task management features
│   ├── __init__.py     # Tasks Blueprint definition
│   └── routes.py       # Tasks routes (dashboard, add, edit, delete, complete)
├── templates/
│   ├── layout.html
│   ├── login.html
│   ├── dashboard.html
│   ├── add_edit_task.html
│   ├── forgot_pin.html
│   ├── set_pin.html
│   └── message.html
└── run.py  


app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'rcc'
app.config['MYSQL_PASSWORD'] = '512'
app.config['MYSQL_DB'] = 'rcmain'

CREATE TABLE `profcv` (
  `id` int NOT NULL AUTO_INCREMENT,
  `user_id` int DEFAULT NULL,
  `name` varchar(255) DEFAULT NULL,
  `email` varchar(255) DEFAULT NULL,
  `cv_data` longtext,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;



use rcmain;
CREATE TABLE IF NOT EXISTS tasks (
    task_id INT PRIMARY KEY AUTO_INCREMENT,
    task_name VARCHAR(255) NOT NULL,
    task_description TEXT,
    task_status VARCHAR(50) DEFAULT 'Pending',
    task_priority VARCHAR(50) DEFAULT 'Medium',
    task_due_date DATE -- Storing as DATE for MySQL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE USER 'rcc'@'localhost' IDENTIFIED BY 'rax';
GRANT ALL PRIVILEGES ON rcmain.* TO 'rcc'@'localhost';
FLUSH PRIVILEGES;
ALTER USER 'rcc'@'localhost' IDENTIFIED BY '512';
FLUSH PRIVILEGES;

pip install flask flask-mysqldb


ALTER TABLE `vemp` ADD COLUMN user_id INT;
UPDATE `vemp` SET user_id = id where id>0
CREATE UNIQUE INDEX idx_user_cv_user_id ON `vemp` (user_id);
