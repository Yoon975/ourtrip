from app.exceptions import NotFoundError
from app.preprocessing.recommendation_preprocessor import RecommendationPreprocessor
from app.repositories.post_repository import PostRepository
from app.repositories.scrap_repository import ScrapRepository
from app.repositories.user_repository import UserRepository
from app.utils.media import media_url


class RecommendationService:
    _model_bundle = None

    def __init__(self, db):
        self.post_repo = PostRepository(db)
        self.scrap_repo = ScrapRepository(db)
        self.user_repo = UserRepository(db)
        self.preprocessor = RecommendationPreprocessor()

    def get_recommendations(self, user_id=None, limit=3):
        posts = self.post_repo.find_all_with_thumbnail()
        if not posts:
            return {"destinations": [], "posts": []}

        if not user_id:
            popular = sorted(posts, key=lambda item: item.get("view_count", 0), reverse=True)
            return {
                "destinations": [],
                "posts": self._attach_media(popular[:limit]),
            }

        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")

        bundle = self._ensure_model()
        age = self.preprocessor.user_age(user.get("birth_year"))
        gender = user.get("gender") or "U"
        destinations = self.preprocessor.predict_destinations(
            bundle,
            age=age,
            gender=gender,
            top_k=3,
        )

        ranked_posts = self.preprocessor.rank_posts_by_destinations(posts, destinations, limit=limit)
        return {
            "destinations": destinations,
            "posts": self._attach_media(ranked_posts),
            "user_features": {"age": age, "gender": gender},
        }

    def get_recommended_posts(self, user_id=None, limit=3):
        return self.get_recommendations(user_id=user_id, limit=limit)["posts"]

    def _ensure_model(self):
        if RecommendationService._model_bundle is not None:
            return RecommendationService._model_bundle

        training_rows = self.post_repo.find_all_for_ml_training()
        scrap_rows = self.scrap_repo.find_all_for_ml_training()
        self.preprocessor.export_training_to_csv(training_rows, scrap_rows)
        RecommendationService._model_bundle = self.preprocessor.train_random_forest()
        return RecommendationService._model_bundle

    def _attach_media(self, posts):
        results = []
        for post in posts:
            post = dict(post)
            post["image_url"] = media_url(post.get("image_url"))
            results.append(post)
        return results

    @classmethod
    def refresh_model(cls):
        cls._model_bundle = None
