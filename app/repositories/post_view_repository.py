class PostViewRepository:
    def __init__(self, db):
        self.db = db

    def record_view(self, user_id, post_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO PostViews (user_id, post_id, view_count, last_viewed_at)
                VALUES (%s, %s, 1, CURRENT_TIMESTAMP)
                ON DUPLICATE KEY UPDATE
                    view_count = view_count + 1,
                    last_viewed_at = CURRENT_TIMESTAMP
                """,
                (user_id, post_id),
            )
        self.db.commit()

    def find_post_ids_by_user(self, user_id, limit=30):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT post_id, view_count
                FROM PostViews
                WHERE user_id = %s
                ORDER BY last_viewed_at DESC
                LIMIT %s
                """,
                (user_id, limit),
            )
            return cursor.fetchall()

    def find_all_for_training(self):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id, post_id, view_count, last_viewed_at
                FROM PostViews
                ORDER BY last_viewed_at DESC
                """
            )
            return cursor.fetchall()
