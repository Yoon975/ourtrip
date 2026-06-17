class NotificationRepository:
    def __init__(self, db):
        self.db = db

    def create(self, user_id, type_, content, actor_id=None, post_id=None, comment_id=None, message_id=None, link_url=None):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Notifications (
                    user_id, type, actor_id, post_id, comment_id, message_id, content, link_url
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (user_id, type_, actor_id, post_id, comment_id, message_id, content, link_url),
            )
            notification_id = cursor.lastrowid
        self.db.commit()
        return notification_id

    def count_unread(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM Notifications WHERE user_id = %s AND is_read = 0",
                (user_id,),
            )
            return cursor.fetchone()["cnt"]

    def find_recent(self, user_id, limit=20):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT n.*, u.nickname AS actor_nickname
                FROM Notifications n
                LEFT JOIN Users u ON n.actor_id = u.user_id
                WHERE n.user_id = %s
                ORDER BY n.created_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            return cursor.fetchall()

    def mark_all_read(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                "UPDATE Notifications SET is_read = 1 WHERE user_id = %s AND is_read = 0",
                (user_id,),
            )
        self.db.commit()
