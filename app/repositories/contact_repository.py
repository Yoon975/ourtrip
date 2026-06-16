class ContactRepository:
    def __init__(self, db):
        self.db = db

    def create(self, name, email, message, user_id=None):
        with self.db.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO Contacts (name, email, message, user_id)
                VALUES (%s, %s, %s, %s)
                """,
                (name, email, message, user_id),
            )
            contact_id = cursor.lastrowid
        self.db.commit()
        return contact_id

    def find_paginated_for_admin(self, page=1, per_page=20, search=None):
        offset = (page - 1) * per_page
        conditions = ["1=1"]
        params = []
        if search:
            conditions.append("(name LIKE %s OR email LIKE %s OR message LIKE %s)")
            params.extend([f"%{search}%"] * 3)
        where = " AND ".join(conditions)
        params.extend([per_page, offset])
        with self.db.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT contact_id, name, email, message, user_id, created_at
                FROM Contacts
                WHERE {where}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                params,
            )
            return cursor.fetchall()

    def count_for_admin(self, search=None):
        conditions = ["1=1"]
        params = []
        if search:
            conditions.append("(name LIKE %s OR email LIKE %s OR message LIKE %s)")
            params.extend([f"%{search}%"] * 3)
        where = " AND ".join(conditions)
        with self.db.cursor() as cursor:
            cursor.execute(f"SELECT COUNT(*) AS cnt FROM Contacts WHERE {where}", params)
            return cursor.fetchone()["cnt"]

    def delete_by_id(self, contact_id):
        with self.db.cursor() as cursor:
            cursor.execute("DELETE FROM Contacts WHERE contact_id = %s", (contact_id,))
        self.db.commit()
