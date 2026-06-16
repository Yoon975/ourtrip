from app.db import get_db
from app.services.auth_service import AuthService
from app.services.comment_service import CommentService
from app.services.post_service import PostService
from app.services.profile_service import ProfileService
from app.services.recommendation_service import RecommendationService
from app.services.scrap_service import ScrapService


def get_auth_service():
    return AuthService(get_db())


def get_post_service():
    return PostService(get_db())


def get_profile_service():
    return ProfileService(get_db())


def get_scrap_service():
    return ScrapService(get_db())


def get_comment_service():
    return CommentService(get_db())


def get_recommendation_service():
    return RecommendationService(get_db())


def get_admin_service():
    from app.services.admin_service import AdminService

    return AdminService(get_db())
