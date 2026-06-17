import pymysql

from app.exceptions import DuplicateError


class UserRepository:
    def __init__(self, db):
        self.db = db

    def find_by_email(self, email):
        with self.db.cursor() as cursor:
            cursor.execute("SELECT * FROM Users WHERE email = %s", (email,))
            return cursor.fetchone()

    def find_by_id(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute("SELECT * FROM Users WHERE user_id = %s", (user_id,))
            return cursor.fetchone()

    def find_paginated_for_admin(self, page=1, per_page=20, role=None, search=None):
        offset = (page - 1) * per_page
        conditions = ["1=1"]
        params = []
        if role:
            conditions.append("role = %s")
            params.append(role)
        if search:
            conditions.append("(email LIKE %s OR nickname LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
        where = " AND ".join(conditions)
        params.extend([per_page, offset])
        with self.db.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT user_id, email, nickname, gender, birth_year, role, created_at
                FROM Users
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params,
            )
            return cursor.fetchall()

    def count_for_admin(self, role=None, search=None):
        conditions = ["1=1"]
        params = []
        if role:
            conditions.append("role = %s")
            params.append(role)
        if search:
            conditions.append("(email LIKE %s OR nickname LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
        where = " AND ".join(conditions)
        with self.db.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS cnt FROM Users WHERE {where}", params)
            return cursor.fetchone()["cnt"]

    def count_by_role(self):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT role, COUNT(*) AS cnt
                FROM Users
                GROUP BY role
                """
            )
            return cursor.fetchall()

    def count_all(self):
        with self.db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS cnt FROM Users")
            return cursor.fetchone()["cnt"]

    def admin_update_user(self, user_id, nickname, gender, birth_year, role, email=None):
        try:
            with self.db.cursor() as cursor:
                if email is not None:
                    cursor.execute(
                        """
                        UPDATE Users
                        SET nickname = %s, gender = %s, birth_year = %s, role = %s, email = %s
                        WHERE user_id = %s
                        """,
                        (nickname, gender, birth_year, role, email, user_id),
                    )
                else:
                    cursor.execute(
                        """
                        UPDATE Users
                        SET nickname = %s, gender = %s, birth_year = %s, role = %s
                        WHERE user_id = %s
                        """,
                        (nickname, gender, birth_year, role, user_id),
                    )
            self.db.commit()
        except pymysql.err.IntegrityError as exc:
            if exc.args[0] == 1062:
                raise DuplicateError("이미 사용 중인 닉네임 또는 이메일입니다.") from exc
            raise

    def delete_by_id(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute("DELETE FROM Users WHERE user_id = %s", (user_id,))
        self.db.commit()

    def create(self, email, password_hash, nickname, gender="U", birth_year=None, profile_image_url=None):
        try:
            with self.db.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO Users (email, password, nickname, gender, birth_year, profile_image_url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (email, password_hash, nickname, gender, birth_year, profile_image_url),
                )
                user_id = cursor.lastrowid
            self.db.commit()
            return user_id
        except pymysql.err.IntegrityError as exc:
            if exc.args[0] == 1062:
                raise DuplicateError("이미 사용 중인 이메일 또는 닉네임입니다.") from exc
            raise

    def update_profile_image(self, user_id, relative_path):
        with self.db.cursor() as cursor:
            cursor.execute(
                "UPDATE Users SET profile_image_url = %s WHERE user_id = %s",
                (relative_path, user_id),
            )
        self.db.commit()

    def update_password(self, user_id, password_hash):
        with self.db.cursor() as cursor:
            cursor.execute(
                "UPDATE Users SET password = %s WHERE user_id = %s",
                (password_hash, user_id),
            )
        self.db.commit()

    def update_email(self, user_id, email):
        try:
            with self.db.cursor() as cursor:
                cursor.execute(
                    "UPDATE Users SET email = %s WHERE user_id = %s",
                    (email, user_id),
                )
            self.db.commit()
        except pymysql.err.IntegrityError as exc:
            if exc.args[0] == 1062:
                raise DuplicateError("이미 사용 중인 이메일입니다.") from exc
            raise

    def update_profile(self, user_id, nickname, gender, birth_year, profile_image_url=None, bio=None, profile_role=None):
        try:
            with self.db.cursor() as cursor:
                fields = ["nickname = %s", "gender = %s", "birth_year = %s"]
                params = [nickname, gender, birth_year]
                if profile_image_url is not None:
                    fields.append("profile_image_url = %s")
                    params.append(profile_image_url)
                if bio is not None:
                    fields.append("bio = %s")
                    params.append(bio)
                if profile_role is not None:
                    fields.append("profile_role = %s")
                    params.append(profile_role)
                params.append(user_id)
                cursor.execute(
                    f"UPDATE Users SET {', '.join(fields)} WHERE user_id = %s",
                    params,
                )
            self.db.commit()
        except pymysql.err.IntegrityError as exc:
            if exc.args[0] == 1062:
                raise DuplicateError("이미 사용 중인 닉네임입니다.") from exc
            raise

    def get_profile_stats(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS cnt FROM Posts WHERE user_id = %s", (user_id,))
            post_count = cursor.fetchone()["cnt"]
            cursor.execute("SELECT COUNT(*) AS cnt FROM Scraps WHERE user_id = %s", (user_id,))
            scrap_count = cursor.fetchone()["cnt"]
            cursor.execute("SELECT COUNT(*) AS cnt FROM Comments WHERE user_id = %s", (user_id,))
            comment_count = cursor.fetchone()["cnt"]
            cursor.execute(
                """
                SELECT COUNT(DISTINCT country) AS cnt FROM (
                    SELECT location_country AS country FROM Posts WHERE user_id = %s
                    UNION
                    SELECT p.location_country AS country
                    FROM Scraps s
                    JOIN Posts p ON s.post_id = p.post_id
                    WHERE s.user_id = %s
                ) AS travel_countries
                """,
                (user_id, user_id),
            )
            country_count = cursor.fetchone()["cnt"]
            cursor.execute(
                """
                SELECT country FROM (
                    SELECT location_country AS country
                    FROM Posts
                    WHERE user_id = %s
                    UNION
                    SELECT p.location_country AS country
                    FROM Scraps s
                    JOIN Posts p ON s.post_id = p.post_id
                    WHERE s.user_id = %s
                ) AS merged
                ORDER BY country
                LIMIT 8
                """,
                (user_id, user_id),
            )
            countries = [row["country"] for row in cursor.fetchall()]
            cursor.execute(
                """
                SELECT post_id, title FROM Posts
                WHERE user_id = %s
                ORDER BY created_at DESC LIMIT 5
                """,
                (user_id,),
            )
            recent_posts = cursor.fetchall()
            cursor.execute(
                """
                SELECT p.post_id, p.title
                FROM Scraps s
                JOIN Posts p ON s.post_id = p.post_id
                WHERE s.user_id = %s
                ORDER BY s.created_at DESC
                LIMIT 5
                """,
                (user_id,),
            )
            scraped_posts = cursor.fetchall()
        return {
            "post_count": post_count,
            "scrap_count": scrap_count,
            "comment_count": comment_count,
            "country_count": country_count,
            "countries": countries,
            "recent_posts": recent_posts,
            "scraped_posts": scraped_posts,
        }
