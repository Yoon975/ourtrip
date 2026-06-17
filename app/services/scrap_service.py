from app.exceptions import NotFoundError
from app.repositories.post_repository import PostRepository
from app.repositories.scrap_repository import ScrapRepository
from app.services.notification_service import NotificationService
from app.utils.media import media_url


class ScrapService:
    def __init__(self, db):
        self.scrap_repo = ScrapRepository(db)
        self.post_repo = PostRepository(db)
        self.notification_service = NotificationService(db)

    def toggle_scrap(self, user_id, post_id):
        post = self.post_repo.find_by_id_with_author(post_id)
        if not post:
            raise NotFoundError("게시글을 찾을 수 없습니다.")

        existing = self.scrap_repo.find(user_id, post_id)
        if existing:
            self.scrap_repo.delete(user_id, post_id)
            scraped = False
        else:
            self.scrap_repo.create(user_id, post_id)
            scraped = True
            from app.repositories.user_repository import UserRepository

            user_row = UserRepository(self.scrap_repo.db).find_by_id(user_id)
            if user_row:
                self.notification_service.notify_scrap(post, user_id, user_row["nickname"])

        return {
            "scraped": scraped,
            "scrap_count": self.scrap_repo.count_by_post(post_id),
        }

    def list_user_scraps(self, user_id, page=1, per_page=12):
        items = self.scrap_repo.find_paginated_by_user(user_id, page, per_page)
        total = self.scrap_repo.count_all_for_user(user_id)
        for item in items:
            item["image_url"] = media_url(item.get("image_url"))
        return items, total
