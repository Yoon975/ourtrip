-- Our Trip feature pack (run once on existing DB)
-- Usage: python scripts/run_migration.py

ALTER TABLE Users ADD COLUMN bio TEXT NULL;
ALTER TABLE Users ADD COLUMN profile_role VARCHAR(50) DEFAULT 'TRAVEL WRITER';

CREATE TABLE IF NOT EXISTS Contacts (
    contact_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    user_id INT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Notifications (
    notification_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    type ENUM('comment', 'reply', 'scrap', 'message') NOT NULL,
    actor_id INT DEFAULT NULL,
    post_id INT DEFAULT NULL,
    comment_id INT DEFAULT NULL,
    message_id INT DEFAULT NULL,
    content VARCHAR(255) DEFAULT NULL,
    link_url VARCHAR(255) DEFAULT NULL,
    is_read TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (actor_id) REFERENCES Users(user_id) ON DELETE SET NULL,
    FOREIGN KEY (post_id) REFERENCES Posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (comment_id) REFERENCES Comments(comment_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Messages (
    message_id INT AUTO_INCREMENT PRIMARY KEY,
    sender_id INT NOT NULL,
    receiver_id INT NOT NULL,
    content TEXT NOT NULL,
    is_read TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (sender_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (receiver_id) REFERENCES Users(user_id) ON DELETE CASCADE
);
