class MessageRepository:
    def __init__(self, db):
        self.db = db

    def create(self, sender_id, receiver_id, content):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Messages (sender_id, receiver_id, content)
                VALUES (%s, %s, %s)
                """,
                (sender_id, receiver_id, content),
            )
            message_id = cursor.lastrowid
        self.db.commit()
        return message_id

    def find_conversation(self, user_id, other_user_id, limit=100):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT m.*, s.nickname AS sender_nickname, r.nickname AS receiver_nickname
                FROM Messages m
                JOIN Users s ON m.sender_id = s.user_id
                JOIN Users r ON m.receiver_id = r.user_id
                WHERE (m.sender_id = %s AND m.receiver_id = %s)
                   OR (m.sender_id = %s AND m.receiver_id = %s)
                ORDER BY m.created_at ASC
                LIMIT %s
                """,
                (user_id, other_user_id, other_user_id, user_id, limit),
            )
            return cursor.fetchall()

    def mark_read_from_sender(self, receiver_id, sender_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE Messages
                SET is_read = 1
                WHERE receiver_id = %s AND sender_id = %s AND is_read = 0
                """,
                (receiver_id, sender_id),
            )
        self.db.commit()

    def count_unread(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM Messages WHERE receiver_id = %s AND is_read = 0",
                (user_id,),
            )
            return cursor.fetchone()["cnt"]

    def list_conversations(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT m.*,
                       CASE WHEN m.sender_id = %s THEN m.receiver_id ELSE m.sender_id END AS other_user_id,
                       CASE WHEN m.sender_id = %s THEN r.nickname ELSE s.nickname END AS other_nickname,
                       CASE WHEN m.sender_id = %s THEN r.profile_image_url ELSE s.profile_image_url END AS other_profile_image_url
                FROM Messages m
                JOIN Users s ON m.sender_id = s.user_id
                JOIN Users r ON m.receiver_id = r.user_id
                WHERE m.sender_id = %s OR m.receiver_id = %s
                ORDER BY m.created_at DESC
                """,
                (user_id, user_id, user_id, user_id, user_id),
            )
            return cursor.fetchall()
