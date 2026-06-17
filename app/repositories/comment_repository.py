class CommentRepository:
    def __init__(self, db):
        self.db = db

    def find_by_post_id(self, post_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.*, u.nickname
                FROM Comments c
                JOIN Users u ON c.user_id = u.user_id
                WHERE c.post_id = %s
                ORDER BY c.created_at ASC
                """,
                (post_id,),
            )
            return cursor.fetchall()

    def find_by_id(self, comment_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM Comments WHERE comment_id = %s",
                (comment_id,),
            )
            return cursor.fetchone()

    def create(self, post_id, user_id, content, parent_id=None):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Comments (post_id, user_id, content, parent_id)
                VALUES (%s, %s, %s, %s)
                """,
                (post_id, user_id, content, parent_id),
            )
            comment_id = cursor.lastrowid
        self.db.commit()
        return comment_id

    def get_with_author(self, comment_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT c.*, u.nickname
                FROM Comments c
                JOIN Users u ON c.user_id = u.user_id
                WHERE c.comment_id = %s
                """,
                (comment_id,),
            )
            return cursor.fetchone()

    def find_paginated_for_admin(self, page=1, per_page=20, search=None):
        offset = (page - 1) * per_page
        conditions = ["1=1"]
        params = []
        if search:
            conditions.append("(c.content LIKE %s OR u.nickname LIKE %s OR p.title LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        where = " AND ".join(conditions)
        params.extend([per_page, offset])
        with self.db.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT c.comment_id, c.content, c.created_at, c.post_id,
                       p.title AS post_title, u.user_id, u.nickname
                FROM Comments c
                JOIN Users u ON c.user_id = u.user_id
                JOIN Posts p ON c.post_id = p.post_id
                WHERE {where}
                ORDER BY c.created_at DESC
                LIMIT %s OFFSET %s
                """,
                params,
            )
            return cursor.fetchall()

    def count_for_admin(self, search=None):
        conditions = ["1=1"]
        params = []
        if search:
            conditions.append("(c.content LIKE %s OR u.nickname LIKE %s OR p.title LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        where = " AND ".join(conditions)
        with self.db.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*) AS cnt
                FROM Comments c
                JOIN Users u ON c.user_id = u.user_id
                JOIN Posts p ON c.post_id = p.post_id
                WHERE {where}
                """,
                params,
            )
            return cursor.fetchone()["cnt"]

    def count_all(self):
        with self.db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS cnt FROM Comments")
            return cursor.fetchone()["cnt"]

    def update(self, comment_id, content):
        with self.db.cursor() as cursor:
            cursor.execute(
                "UPDATE Comments SET content = %s WHERE comment_id = %s",
                (content, comment_id),
            )
        self.db.commit()

    def delete_by_id(self, comment_id):
        with self.db.cursor() as cursor:
            cursor.execute("DELETE FROM Comments WHERE comment_id = %s", (comment_id,))
        self.db.commit()
