from app.exceptions import ForbiddenError, NotFoundError
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

    def create_post(self, user_id, payload, image_files=None, image_file=None):
        data = validate_post_payload(payload)
        post_id = self.post_repo.create(user_id=user_id, **data)
        files = self._normalize_image_files(image_files, image_file)
        for index, file in enumerate(files, start=1):
            if file and file.filename:
                image_path = self.image_service.save_post_image(file)
                self.post_repo.add_image(post_id, image_path, index)
        return post_id

    def update_post(self, user_id, post_id, payload, image_files=None, replace_images=False):
        post = self.post_repo.find_by_id_with_author(post_id)
        if not post:
            raise NotFoundError("게시글을 찾을 수 없습니다.")
        if post["user_id"] != user_id:
            raise ForbiddenError("본인 게시글만 수정할 수 있습니다.")

        data = validate_post_payload(payload)
        self.post_repo.update(post_id, **data)

        files = self._normalize_image_files(image_files)
        if replace_images and files:
            old_images = self.post_repo.find_images_by_post(post_id)
            self.post_repo.delete_images_by_post(post_id)
            for row in old_images:
                self.image_service.delete_relative(row["image_url"])
            for index, file in enumerate(files, start=1):
                if file and file.filename:
                    image_path = self.image_service.save_post_image(file)
                    self.post_repo.add_image(post_id, image_path, index)
        elif files:
            existing = self.post_repo.find_images_by_post(post_id)
            start_order = len(existing) + 1
            for offset, file in enumerate(files):
                if file and file.filename:
                    image_path = self.image_service.save_post_image(file)
                    self.post_repo.add_image(post_id, image_path, start_order + offset)

        return post_id

    def delete_post(self, user_id, post_id, is_admin=False):
        post = self.post_repo.find_by_id_with_author(post_id)
        if not post:
            raise NotFoundError("게시글을 찾을 수 없습니다.")
        if not is_admin and post["user_id"] != user_id:
            raise ForbiddenError("본인 게시글만 삭제할 수 있습니다.")

        images = self.post_repo.find_images_by_post(post_id)
        self.post_repo.delete_by_id(post_id)
        for row in images:
            self.image_service.delete_relative(row["image_url"])
        return {"post_id": post_id}

    def get_post_for_edit(self, user_id, post_id):
        post = self.post_repo.find_by_id_with_author(post_id)
        if not post:
            raise NotFoundError("게시글을 찾을 수 없습니다.")
        if post["user_id"] != user_id:
            raise ForbiddenError("본인 게시글만 수정할 수 있습니다.")
        images = self.post_repo.find_images_by_post(post_id)
        post["images"] = [media_url(row["image_url"]) for row in images]
        return post

    def list_posts(self, page=1, per_page=12, search=None, country=None, city=None):
        posts = self.post_repo.find_paginated_with_thumbnail(
            page, per_page, search=search, country=country, city=city
        )
        total = self.post_repo.count_filtered(search=search, country=country, city=city)
        for post in posts:
            post["image_url"] = media_url(post.get("image_url"))
        return posts, total

    def list_countries(self):
        return self.post_repo.list_filter_countries()

    def list_user_posts(self, user_id, page=1, per_page=12):
        posts = self.post_repo.find_paginated_by_user(user_id, page, per_page)
        total = self.post_repo.count_by_user(user_id)
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
            "can_edit": viewer_user_id == post["user_id"],
        }

    def _normalize_image_files(self, image_files=None, image_file=None):
        files = []
        if image_files:
            files.extend([file for file in image_files if file and file.filename])
        if image_file and image_file.filename:
            files.append(image_file)
        return files
