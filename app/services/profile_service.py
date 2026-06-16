from app.exceptions import NotFoundError
from app.repositories.user_repository import UserRepository
from app.services.image_service import ImageService
from app.utils.media import media_url
from app.validators.auth_validator import validate_profile_update_payload


GENDER_LABELS = {"M": "남성", "F": "여성", "U": "미선택"}


class ProfileService:
    def __init__(self, db):
        self.user_repo = UserRepository(db)
        self.image_service = ImageService()

    def get_profile(self, user_id):
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")

        stats_bundle = self.user_repo.get_profile_stats(user_id)
        user["profile_image_url"] = media_url(user.get("profile_image_url"))

        return {
            "user": user,
            "stats": {
                "post_count": stats_bundle["post_count"],
                "scrap_count": stats_bundle["scrap_count"],
                "comment_count": stats_bundle["comment_count"],
                "country_count": stats_bundle["country_count"],
            },
            "countries": stats_bundle["countries"],
            "recent_posts": stats_bundle["recent_posts"],
            "scraped_posts": stats_bundle["scraped_posts"],
            "gender_label": GENDER_LABELS.get(user.get("gender", "U"), "미선택"),
        }

    def update_profile(self, user_id, payload, profile_file=None):
        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")

        nickname = (payload.get("nickname") or payload.get("nick") or "").strip()
        gender = payload.get("gender")
        birth_year_raw = payload.get("birth_year")
        birth_year = int(birth_year_raw) if birth_year_raw not in (None, "") else None

        validate_profile_update_payload(
            {"nickname": nickname, "gender": gender, "birth_year": birth_year}
        )

        profile_image_url = None
        if profile_file and profile_file.filename:
            profile_image_url = self.image_service.save_profile_image(profile_file)
            old_path = user.get("profile_image_url")
            if old_path:
                self.image_service.delete_relative(old_path)

        self.user_repo.update_profile(
            user_id=user_id,
            nickname=nickname,
            gender=gender,
            birth_year=birth_year,
            profile_image_url=profile_image_url,
            bio=(payload.get("bio") or "").strip() or None,
            profile_role=(payload.get("profile_role") or "").strip() or "TRAVEL WRITER",
        )

        return {"user_id": user_id, "nickname": nickname}

    def list_user_posts(self, user_id, page=1, per_page=12):
        from app.repositories.post_repository import PostRepository
        from app.utils.media import media_url

        repo = PostRepository(self.user_repo.db)
        posts = repo.find_paginated_by_user(user_id, page, per_page)
        total = repo.count_by_user(user_id)
        for post in posts:
            post["image_url"] = media_url(post.get("image_url"))
        return posts, total
