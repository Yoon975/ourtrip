class PostRepository:
    def __init__(self, db):
        self.db = db

    def find_paginated_with_thumbnail(self, page=1, per_page=12, search=None, country=None, city=None):
        offset = (page - 1) * per_page
        conditions = ["1=1"]
        params = []
        if search:
            conditions.append("(p.title LIKE %s OR p.content LIKE %s OR u.nickname LIKE %s)")
            params.extend([f"%{search}%"] * 3)
        if country:
            conditions.append("p.location_country = %s")
            params.append(country)
        if city:
            conditions.append("p.location_city LIKE %s")
            params.append(f"%{city}%")
        where = " AND ".join(conditions)
        params.extend([per_page, offset])
        with self.db.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT p.*, u.nickname,
                       (SELECT image_url FROM Post_Images pi
                        WHERE pi.post_id = p.post_id
                        ORDER BY pi.image_order LIMIT 1) AS image_url
                FROM Posts p
                JOIN Users u ON p.user_id = u.user_id
                WHERE {where}
                ORDER BY p.created_at DESC
                LIMIT %s OFFSET %s
                """,
                params,
            )
            return cursor.fetchall()

    def count_filtered(self, search=None, country=None, city=None):
        conditions = ["1=1"]
        params = []
        if search:
            conditions.append("(p.title LIKE %s OR p.content LIKE %s OR u.nickname LIKE %s)")
            params.extend([f"%{search}%"] * 3)
        if country:
            conditions.append("p.location_country = %s")
            params.append(country)
        if city:
            conditions.append("p.location_city LIKE %s")
            params.append(f"%{city}%")
        where = " AND ".join(conditions)
        with self.db.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*) AS cnt
                FROM Posts p
                JOIN Users u ON p.user_id = u.user_id
                WHERE {where}
                """,
                params,
            )
            return cursor.fetchone()["cnt"]

    def list_filter_countries(self):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT DISTINCT location_country AS country
                FROM Posts
                WHERE location_country IS NOT NULL AND location_country != ''
                ORDER BY location_country
                """
            )
            return [row["country"] for row in cursor.fetchall()]

    def find_paginated_by_user(self, user_id, page=1, per_page=12):
        offset = (page - 1) * per_page
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.*,
                       (SELECT image_url FROM Post_Images pi
                        WHERE pi.post_id = p.post_id
                        ORDER BY pi.image_order LIMIT 1) AS image_url
                FROM Posts p
                WHERE p.user_id = %s
                ORDER BY p.created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, per_page, offset),
            )
            return cursor.fetchall()

    def count_by_user(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS cnt FROM Posts WHERE user_id = %s", (user_id,))
            return cursor.fetchone()["cnt"]

    def update(
        self,
        post_id,
        title,
        content,
        location_country,
        location_city=None,
        travel_start_date=None,
        travel_end_date=None,
    ):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                UPDATE Posts
                SET title = %s, content = %s, location_country = %s, location_city = %s,
                    travel_start_date = %s, travel_end_date = %s
                WHERE post_id = %s
                """,
                (
                    title,
                    content,
                    location_country,
                    location_city,
                    travel_start_date,
                    travel_end_date,
                    post_id,
                ),
            )
        self.db.commit()

    def delete_images_by_post(self, post_id):
        with self.db.cursor() as cursor:
            cursor.execute("DELETE FROM Post_Images WHERE post_id = %s", (post_id,))
        self.db.commit()

    def count_all(self):
        with self.db.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS cnt FROM Posts")
            return cursor.fetchone()["cnt"]

    def find_all_with_thumbnail(self):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.*, u.nickname,
                       (SELECT image_url FROM Post_Images pi
                        WHERE pi.post_id = p.post_id
                        ORDER BY pi.image_order LIMIT 1) AS image_url
                FROM Posts p
                JOIN Users u ON p.user_id = u.user_id
                ORDER BY p.created_at DESC
                """
            )
            return cursor.fetchall()

    def find_by_id_with_author(self, post_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.*, u.nickname,
                       (SELECT image_url FROM Post_Images pi
                        WHERE pi.post_id = p.post_id
                        ORDER BY pi.image_order LIMIT 1) AS image_url
                FROM Posts p
                JOIN Users u ON p.user_id = u.user_id
                WHERE p.post_id = %s
                """,
                (post_id,),
            )
            return cursor.fetchone()

    def increment_view_count(self, post_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                "UPDATE Posts SET view_count = view_count + 1 WHERE post_id = %s",
                (post_id,),
            )
        self.db.commit()

    def find_images_by_post(self, post_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT image_url FROM Post_Images
                WHERE post_id = %s
                ORDER BY image_order ASC
                """,
                (post_id,),
            )
            return cursor.fetchall()

    def add_image(self, post_id, relative_path, image_order=1):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Post_Images (post_id, image_url, image_order)
                VALUES (%s, %s, %s)
                """,
                (post_id, relative_path, image_order),
            )
        self.db.commit()

    def create(
        self,
        user_id,
        title,
        content,
        location_country,
        location_city=None,
        travel_start_date=None,
        travel_end_date=None,
    ):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Posts (
                    user_id, title, content, location_country, location_city,
                    travel_start_date, travel_end_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    user_id,
                    title,
                    content,
                    location_country,
                    location_city,
                    travel_start_date,
                    travel_end_date,
                ),
            )
            post_id = cursor.lastrowid
        self.db.commit()
        return post_id

    def find_all_for_ml_training(self):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT p.post_id, p.user_id, p.title, p.content,
                       p.location_country, p.location_city,
                       p.travel_start_date, p.travel_end_date,
                       p.view_count, p.created_at,
                       u.birth_year, u.gender, u.nickname
                FROM Posts p
                JOIN Users u ON p.user_id = u.user_id
                WHERE p.location_country IS NOT NULL
                  AND p.location_country != ''
                ORDER BY p.post_id
                """
            )
            return cursor.fetchall()

    def find_post_ids_by_user(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                "SELECT post_id FROM Posts WHERE user_id = %s",
                (user_id,),
            )
            return {row["post_id"] for row in cursor.fetchall()}

    def find_all_for_content_index(self):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT post_id, title, content, location_country, location_city, view_count
                FROM Posts
                WHERE location_country IS NOT NULL AND location_country != ''
                ORDER BY post_id
                """
            )
            return cursor.fetchall()

    def find_country_stats_by_user(self, user_id):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT location_country AS country,
                       COUNT(*) AS cnt,
                       AVG(
                           GREATEST(DATEDIFF(travel_end_date, travel_start_date) + 1, 0)
                       ) AS avg_duration,
                       AVG(MONTH(travel_start_date)) AS avg_month
                FROM Posts
                WHERE user_id = %s
                  AND location_country IS NOT NULL
                  AND location_country != ''
                GROUP BY location_country
                """,
                (user_id,),
            )
            return cursor.fetchall()

    def find_paginated_for_admin(self, page=1, per_page=20, country=None, search=None):
        offset = (page - 1) * per_page
        conditions = ["1=1"]
        params = []
        if country:
            conditions.append("p.location_country = %s")
            params.append(country)
        if search:
            conditions.append("(p.title LIKE %s OR u.nickname LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
        where = " AND ".join(conditions)
        params.extend([per_page, offset])
        with self.db.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT p.post_id, p.title, p.view_count, p.created_at,
                       p.location_country, p.location_city,
                       u.user_id, u.nickname
                FROM Posts p
                JOIN Users u ON p.user_id = u.user_id
                WHERE {where}
                ORDER BY p.created_at DESC
                LIMIT %s OFFSET %s
                """,
                params,
            )
            return cursor.fetchall()

    def count_for_admin(self, country=None, search=None):
        conditions = ["1=1"]
        params = []
        if country:
            conditions.append("p.location_country = %s")
            params.append(country)
        if search:
            conditions.append("(p.title LIKE %s OR u.nickname LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
        where = " AND ".join(conditions)
        with self.db.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT COUNT(*) AS cnt
                FROM Posts p
                JOIN Users u ON p.user_id = u.user_id
                WHERE {where}
                """,
                params,
            )
            return cursor.fetchone()["cnt"]

    def count_by_country(self):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                SELECT location_country AS country, COUNT(*) AS cnt
                FROM Posts
                GROUP BY location_country
                ORDER BY cnt DESC
                LIMIT 12
                """
            )
            return cursor.fetchall()

    def delete_by_id(self, post_id):
        with self.db.cursor() as cursor:
            cursor.execute("DELETE FROM Posts WHERE post_id = %s", (post_id,))
        self.db.commit()
