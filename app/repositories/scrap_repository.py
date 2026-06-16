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
