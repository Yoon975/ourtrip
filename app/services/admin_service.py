from app.exceptions import NotFoundError
from app.repositories.comment_repository import CommentRepository
from app.repositories.contact_repository import ContactRepository
from app.repositories.post_repository import PostRepository
from app.repositories.scrap_repository import ScrapRepository
from app.repositories.user_repository import UserRepository
from app.services.image_service import ImageService
from app.services.recommendation_service import RecommendationService
from app.validators.auth_validator import validate_admin_user_update

class AdminService:
    PER_PAGE = 20

    def __init__(self, db):
        self.db = db
        self.user_repo = UserRepository(db)
        self.post_repo = PostRepository(db)
        self.comment_repo = CommentRepository(db)
        self.scrap_repo = ScrapRepository(db)
        self.contact_repo = ContactRepository(db)
        self.image_service = ImageService()

    def get_overview(self):
        return {
            "totals": {
                "users": self.user_repo.count_all(),
                "posts": self.post_repo.count_all(),
                "comments": self.comment_repo.count_all(),
                "scraps": self.scrap_repo.count_all(),
            },
            "users_by_role": self.user_repo.count_by_role(),
            "posts_by_country": self.post_repo.count_by_country(),
            "model_metrics": RecommendationService(self.db).get_model_status(),
        }

    def train_recommendation_model(self):
        return RecommendationService(self.db).train_model()

    def list_users(self, page=1, role=None, search=None):
        per_page = self.PER_PAGE
        items = self.user_repo.find_paginated_for_admin(page, per_page, role, search)
        total = self.user_repo.count_for_admin(role, search)
        return self._paginate(items, page, per_page, total)

    def list_posts(self, page=1, country=None, search=None):
        per_page = self.PER_PAGE
        items = self.post_repo.find_paginated_for_admin(page, per_page, country, search)
        total = self.post_repo.count_for_admin(country, search)
        return self._paginate(items, page, per_page, total)

    def list_comments(self, page=1, search=None):
        per_page = self.PER_PAGE
        items = self.comment_repo.find_paginated_for_admin(page, per_page, search)
        total = self.comment_repo.count_for_admin(search)
        return self._paginate(items, page, per_page, total)

    def list_countries(self):
        return [row["country"] for row in self.post_repo.count_by_country()]

    def list_scraps(self, page=1, search=None):
        per_page = self.PER_PAGE
        items = self.scrap_repo.find_paginated_for_admin(page, per_page, search)
        total = self.scrap_repo.count_for_admin(search)
        return self._paginate(items, page, per_page, total)

    def delete_scrap(self, scrap_id):
        self.scrap_repo.admin_delete(scrap_id)
        return {"scrap_id": scrap_id}

    def list_contacts(self, page=1, search=None):
        per_page = self.PER_PAGE
        items = self.contact_repo.find_paginated_for_admin(page, per_page, search)
        total = self.contact_repo.count_for_admin(search)
        return self._paginate(items, page, per_page, total)

    def delete_contact(self, contact_id):
        self.contact_repo.delete_by_id(contact_id)
        return {"contact_id": contact_id}

    def delete_user(self, user_id):
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        self.user_repo.delete_by_id(user_id)
        return {"user_id": user_id}

    def update_user(self, user_id, payload):
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")

        nickname = (payload.get("nickname") or payload.get("nick") or "").strip()
        gender = payload.get("gender")
        role = payload.get("role", "user")
        email = (payload.get("email") or "").strip() or None
        birth_year_raw = payload.get("birth_year")
        birth_year = int(birth_year_raw) if birth_year_raw not in (None, "") else None

        validate_admin_user_update(
            {
                "nickname": nickname,
                "gender": gender,
                "birth_year": birth_year,
                "role": role,
                "email": email or user["email"],
            }
        )

        self.user_repo.admin_update_user(user_id, nickname, gender, birth_year, role, email=email)
        return {"user_id": user_id, "nickname": nickname, "role": role, "email": email or user["email"]}

    def delete_post(self, post_id):
        post = self.post_repo.find_by_id_with_author(post_id)
        if not post:
            raise NotFoundError("게시글을 찾을 수 없습니다.")

        images = self.post_repo.find_images_by_post(post_id)
        self.post_repo.delete_by_id(post_id)

        for row in images:
            self.image_service.delete_relative(row["image_url"])

        return {"post_id": post_id}

    def delete_comment(self, comment_id):
        comment = self.comment_repo.find_by_id(comment_id)
        if not comment:
            raise NotFoundError("댓글을 찾을 수 없습니다.")

        self.comment_repo.delete_by_id(comment_id)
        return {"comment_id": comment_id}

    def _paginate(self, items, page, per_page, total):
        total_pages = max((total + per_page - 1) // per_page, 1)
        return {
            "items": items,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        }

    def _serialize_row(self, row):
        data = dict(row)
        for key, value in data.items():
            if hasattr(value, "strftime"):
                data[key] = value.strftime("%Y-%m-%d %H:%M:%S")
        return data

    def serialize_scraps_page(self, page_data):
        return {
            **page_data,
            "items": [self._serialize_row(item) for item in page_data["items"]],
        }

    def serialize_contacts_page(self, page_data):
        return {
            **page_data,
            "items": [self._serialize_row(item) for item in page_data["items"]],
        }

    def serialize_users_page(self, page_data):
        return {
            **page_data,
            "items": [self._serialize_row(item) for item in page_data["items"]],
        }

    def serialize_posts_page(self, page_data):
        return {
            **page_data,
            "items": [self._serialize_row(item) for item in page_data["items"]],
        }

    def serialize_comments_page(self, page_data):
        return {
            **page_data,
            "items": [self._serialize_row(item) for item in page_data["items"]],
        }
