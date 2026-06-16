from app.exceptions import NotFoundError
from app.preprocessing.hybrid_recommender import HybridRecommender
from app.preprocessing.recommendation_preprocessor import RecommendationPreprocessor
from app.repositories.post_repository import PostRepository
from app.repositories.scrap_repository import ScrapRepository
from app.repositories.user_repository import UserRepository
from app.utils.media import media_url


class RecommendationService:
    _model_bundle = None

    def __init__(self, db):
        self.db = db
        self.post_repo = PostRepository(db)
        self.scrap_repo = ScrapRepository(db)
        self.user_repo = UserRepository(db)
        self.preprocessor = RecommendationPreprocessor()
        self.hybrid = HybridRecommender()
    def get_recommendations(self, user_id=None, limit=3):
        posts = self.post_repo.find_all_with_thumbnail()
        if not posts:
            return {"destinations": [], "posts": [], "model_ready": False}

        if not user_id:
            popular = sorted(posts, key=lambda item: item.get("view_count", 0), reverse=True)
            return {
                "destinations": [],
                "posts": self._attach_media(popular[:limit]),
                "model_ready": self._load_model() is not None,
            }

        user = self.user_repo.find_by_id(user_id)
        if not user:
            raise NotFoundError("사용자를 찾을 수 없습니다.")

        bundle = self._load_model()
        age = self.preprocessor.user_age(user.get("birth_year"))
        gender = user.get("gender") or "U"
        scrap_stats = self.scrap_repo.find_country_stats_by_user(user_id)
        post_stats = self.post_repo.find_country_stats_by_user(user_id)
        history_count = sum(int(row.get("cnt") or 0) for row in scrap_stats + post_stats)

        if bundle is None:
            popular = sorted(posts, key=lambda item: item.get("view_count", 0), reverse=True)
            return {
                "destinations": [],
                "posts": self._attach_media(popular[:limit]),
                "user_features": {
                    "age": age,
                    "gender": gender,
                    "history_count": history_count,
                },
                "model_ready": False,
            }

        destinations = self.preprocessor.predict_destinations(
            bundle,
            age=age,
            gender=gender,
            scrap_stats=scrap_stats,
            post_stats=post_stats,
            top_k=3,
        )
        ranked_posts = self._rank_posts(bundle, user_id, posts, destinations, scrap_stats, post_stats, limit)
        return {
            "destinations": destinations,
            "posts": self._attach_media(ranked_posts),
            "user_features": {
                "age": age,
                "gender": gender,
                "history_count": history_count,
            },
            "model_ready": True,
            "hybrid_ready": bundle.get("hybrid_artifacts") is not None,
        }

    def get_recommended_posts(self, user_id=None, limit=3):
        return self.get_recommendations(user_id=user_id, limit=limit)["posts"]

    def train_model(self):
        training_rows = self.post_repo.find_all_for_ml_training()
        scrap_rows = self.scrap_repo.find_all_for_ml_training()
        self.preprocessor.export_training_to_csv(training_rows, scrap_rows)
        bundle = self.preprocessor.train_random_forest()

        content_posts = self.post_repo.find_all_for_content_index()
        scrap_pairs = self.scrap_repo.find_all_pairs()
        bundle["hybrid_artifacts"] = self.hybrid.build_artifacts(content_posts, scrap_pairs)
        bundle["model_version"] = 3

        metrics = self.preprocessor.evaluate_model_metrics(self.db)
        hybrid_metrics = self._evaluate_hybrid_ranking(bundle, scrap_rows)
        rf_rank_metrics = self._evaluate_ranking_baseline(bundle, scrap_rows, use_hybrid=False)
        if hybrid_metrics:
            metrics["hybrid_country_hit_at_3"] = hybrid_metrics.get("country_hit_at_3")
            metrics["hybrid_post_hit_at_3"] = hybrid_metrics.get("post_hit_at_3")
            metrics["hybrid_evaluated"] = hybrid_metrics.get("evaluated")
        if rf_rank_metrics:
            metrics["rf_rank_country_hit_at_3"] = rf_rank_metrics.get("country_hit_at_3")

        bundle["metrics"] = metrics
        self.preprocessor.save_model_bundle(bundle)
        RecommendationService._model_bundle = bundle
        return {
            "trained_at": bundle.get("trained_at"),
            "sample_count": bundle.get("sample_count"),
            "metrics": metrics,
        }

    def get_model_status(self):
        bundle = self._load_model()
        if bundle is None:
            return {
                "exists": False,
                "trained_at": None,
                "sample_count": None,
                "top1_accuracy": None,
                "top3_accuracy": None,
            }

        metrics = bundle.get("metrics") or {}
        feature_columns = bundle.get("feature_columns") or []
        return {
            "exists": True,
            "trained_at": bundle.get("trained_at"),
            "sample_count": bundle.get("sample_count"),
            "top1_accuracy": metrics.get("top1_accuracy"),
            "top3_accuracy": metrics.get("top3_accuracy"),
            "feature_count": metrics.get("feature_count") or len(feature_columns),
            "hybrid_enabled": bundle.get("hybrid_artifacts") is not None,
            "hybrid_country_hit_at_3": metrics.get("hybrid_country_hit_at_3"),
            "hybrid_post_hit_at_3": metrics.get("hybrid_post_hit_at_3"),
            "rf_rank_country_hit_at_3": metrics.get("rf_rank_country_hit_at_3"),
            "note": metrics.get("note"),
        }

    def _load_model(self):
        if RecommendationService._model_bundle is not None:
            return RecommendationService._model_bundle

        bundle = self.preprocessor.load_model_bundle()
        RecommendationService._model_bundle = bundle
        return bundle

    def _rank_posts(self, bundle, user_id, posts, destinations, scrap_stats, post_stats, limit):
        artifacts = bundle.get("hybrid_artifacts")
        if artifacts:
            scrap_post_ids = self.scrap_repo.find_post_ids_by_user(user_id)
            own_post_ids = self.post_repo.find_post_ids_by_user(user_id)
            ranked = self.hybrid.rank_posts(
                artifacts,
                user_id,
                posts,
                destinations,
                scrap_post_ids,
                own_post_ids,
                limit=limit,
            )
            if ranked:
                return ranked

        return self.preprocessor.rank_posts_by_destinations(posts, destinations, limit=limit)

    def _evaluate_hybrid_ranking(self, bundle, scrap_rows):
        return self._evaluate_ranking_baseline(bundle, scrap_rows, use_hybrid=True)

    def _evaluate_ranking_baseline(self, bundle, scrap_rows, use_hybrid=True):
        artifacts = bundle.get("hybrid_artifacts")
        if use_hybrid and not artifacts:
            return None

        catalog_posts = self.post_repo.find_all_for_content_index()

        def rank_fn(user_id, scrap_post_ids, own_post_ids):
            user = self.user_repo.find_by_id(user_id)
            if not user:
                return []
            age = self.preprocessor.user_age(user.get("birth_year"))
            gender = user.get("gender") or "U"
            scrap_stats = self.scrap_repo.find_country_stats_by_user(user_id)
            post_stats = self.post_repo.find_country_stats_by_user(user_id)
            destinations = self.preprocessor.predict_destinations(
                bundle,
                age=age,
                gender=gender,
                scrap_stats=scrap_stats,
                post_stats=post_stats,
                top_k=3,
            )
            if use_hybrid:
                return self.hybrid.rank_posts(
                    artifacts,
                    user_id,
                    catalog_posts,
                    destinations,
                    scrap_post_ids,
                    own_post_ids,
                    limit=3,
                )
            return self.preprocessor.rank_posts_by_destinations(
                catalog_posts,
                destinations,
                limit=3,
            )

        if use_hybrid:
            return self.hybrid.evaluate_recommendations(scrap_rows, rank_fn)
        return self.hybrid.evaluate_recommendations(scrap_rows, rank_fn)

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
