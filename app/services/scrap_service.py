from app.exceptions import NotFoundError
from app.repositories.post_repository import PostRepository
from app.repositories.scrap_repository import ScrapRepository


class ScrapService:
    def __init__(self, db):
        self.scrap_repo = ScrapRepository(db)
        self.post_repo = PostRepository(db)

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

        return {
            "scraped": scraped,
            "scrap_count": self.scrap_repo.count_by_post(post_id),
        }
