import pymysql

from app.exceptions import DuplicateError


class ScrapRepository:
    def __init__(self, db):
        self.db = db

    def find(self, user_id, post_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM Scraps WHERE user_id = %s AND post_id = %s",
                (user_id, post_id),
            )
            return cursor.fetchone()

    def create(self, user_id, post_id):
        try:
            with self.db.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO Scraps (user_id, post_id) VALUES (%s, %s)",
                    (user_id, post_id),
                )
            self.db.commit()
        except pymysql.err.IntegrityError as exc:
            if exc.args[0] == 1062:
                raise DuplicateError("이미 스크랩한 게시글입니다.") from exc
            raise

    def delete(self, user_id, post_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                "DELETE FROM Scraps WHERE user_id = %s AND post_id = %s",
                (user_id, post_id),
            )
        self.db.commit()

    def count_by_post(self, post_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) AS cnt FROM Scraps WHERE post_id = %s",
                (post_id,),
            )
            return cursor.fetchone()["cnt"]

    def find_post_ids_by_user(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                "SELECT post_id FROM Scraps WHERE user_id = %s",
                (user_id,),
            )
            return {row["post_id"] for row in cursor.fetchall()}

    def count_all(self):
        with self.db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS cnt FROM Scraps")
            return cursor.fetchone()["cnt"]

    def find_all_for_ml_training(self):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT s.scrap_id, s.user_id, s.post_id, s.created_at,
                       u.birth_year, u.gender, u.nickname,
                       p.location_country, p.location_city, p.view_count,
                       p.travel_start_date, p.travel_end_date
                FROM Scraps s
                JOIN Users u ON s.user_id = u.user_id
                JOIN Posts p ON s.post_id = p.post_id
                WHERE p.location_country IS NOT NULL AND p.location_country != ''
                ORDER BY s.scrap_id
                """
            )
            return cursor.fetchall()

    def count_all_for_user(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS cnt FROM Scraps WHERE user_id = %s", (user_id,))
            return cursor.fetchone()["cnt"]

    def find_paginated_by_user(self, user_id, page=1, per_page=12):
        offset = (page - 1) * per_page
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT s.scrap_id, s.created_at,
                       p.post_id, p.title, p.location_country, p.location_city,
                       (SELECT image_url FROM Post_Images pi
                        WHERE pi.post_id = p.post_id
                        ORDER BY pi.image_order LIMIT 1) AS image_url
                FROM Scraps s
                JOIN Posts p ON s.post_id = p.post_id
                WHERE s.user_id = %s
                ORDER BY s.created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, per_page, offset),
            )
            return cursor.fetchall()

    def find_paginated_for_admin(self, page=1, per_page=20, search=None):
        offset = (page - 1) * per_page
        conditions = ["1=1"]
        params = []
        if search:
            conditions.append("(u.nickname LIKE %s OR p.title LIKE %s OR p.location_country LIKE %s)")
            params.extend([f"%{search}%"] * 3)
        where = " AND ".join(conditions)
        params.extend([per_page, offset])
        with self.db.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT s.scrap_id, s.created_at, s.user_id, s.post_id,
                       u.nickname, p.title, p.location_country
                FROM Scraps s
                JOIN Users u ON s.user_id = u.user_id
                JOIN Posts p ON s.post_id = p.post_id
                WHERE {where}
                ORDER BY s.created_at DESC
                LIMIT %s OFFSET %s
                """,
                params,
            )
            return cursor.fetchall()

    def count_for_admin(self, search=None):
        conditions = ["1=1"]
        params = []
        if search:
            conditions.append("(u.nickname LIKE %s OR p.title LIKE %s OR p.location_country LIKE %s)")
            params.extend([f"%{search}%"] * 3)
        where = " AND ".join(conditions)
        with self.db.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*) AS cnt
                FROM Scraps s
                JOIN Users u ON s.user_id = u.user_id
                JOIN Posts p ON s.post_id = p.post_id
                WHERE {where}
                """,
                params,
            )
            return cursor.fetchone()["cnt"]

    def admin_delete(self, scrap_id):
        with self.db.cursor() as cursor:
            cursor.execute("DELETE FROM Scraps WHERE scrap_id = %s", (scrap_id,))
        self.db.commit()

    def find_all_pairs(self):
        with self.db.cursor() as cursor:
            cursor.execute("SELECT user_id, post_id FROM Scraps ORDER BY scrap_id")
            return cursor.fetchall()

    def find_country_stats_by_user(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.location_country AS country,
                       COUNT(*) AS cnt,
                       AVG(
                           GREATEST(DATEDIFF(p.travel_end_date, p.travel_start_date) + 1, 0)
                       ) AS avg_duration,
                       AVG(MONTH(p.travel_start_date)) AS avg_month
                FROM Scraps s
                JOIN Posts p ON s.post_id = p.post_id
                WHERE s.user_id = %s
                  AND p.location_country IS NOT NULL
                  AND p.location_country != ''
                GROUP BY p.location_country
                """,
                (user_id,),
            )
            return cursor.fetchall()
