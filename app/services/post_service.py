from app.exceptions import NotFoundError
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.repositories.scrap_repository import ScrapRepository
from app.services.comment_service import CommentService
from app.services.image_service import ImageService
from app.utils.media import media_url
from app.validators.post_validator import validate_post_payload


class PostService:
    def __init__(self, db):
        self.post_repo = PostRepository(db)
        self.scrap_repo = ScrapRepository(db)
        self.comment_repo = CommentRepository(db)
        self.comment_service = CommentService(db)
        self.image_service = ImageService()

    def create_post(self, user_id, payload, image_file=None):
        data = validate_post_payload(payload)
        post_id = self.post_repo.create(user_id=user_id, **data)

        if image_file and image_file.filename:
            image_path = self.image_service.save_post_image(image_file)
            self.post_repo.add_image(post_id, image_path, 1)

        return post_id

    def list_posts(self, page=1, per_page=12):
        posts = self.post_repo.find_paginated_with_thumbnail(page, per_page)
        total = self.post_repo.count_all()
        for post in posts:
            post["image_url"] = media_url(post.get("image_url"))
        return posts, total

    def list_posts_all(self):
        posts = self.post_repo.find_all_with_thumbnail()
        for post in posts:
            post["image_url"] = media_url(post.get("image_url"))
        return posts

    def get_post_detail(self, post_id, viewer_user_id=None):
        post = self.post_repo.find_by_id_with_author(post_id)
        if not post:
            raise NotFoundError("게시글을 찾을 수 없습니다.")

        self.post_repo.increment_view_count(post_id)
        post["view_count"] = (post.get("view_count") or 0) + 1
        post["image_url"] = media_url(post.get("image_url"))

        images = self.post_repo.find_images_by_post(post_id)
        post["images"] = [media_url(row["image_url"]) for row in images]

        comments = self.comment_service.get_hierarchical_comments(post_id)
        is_scraped = False
        scrap_count = self.scrap_repo.count_by_post(post_id)
        if viewer_user_id:
            is_scraped = self.scrap_repo.find(viewer_user_id, post_id) is not None

        return {
            "post": post,
            "comments": comments,
            "is_scraped": is_scraped,
            "scrap_count": scrap_count,
        }
