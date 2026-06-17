from app.exceptions import NotFoundError
from app.preprocessing.hybrid_recommender import HybridRecommender
from app.preprocessing.recommendation_preprocessor import RecommendationPreprocessor
from app.preprocessing.stage3_recommender import Stage3Recommender
from app.repositories.post_repository import PostRepository
from app.repositories.post_view_repository import PostViewRepository
from app.repositories.scrap_repository import ScrapRepository
from app.repositories.user_repository import UserRepository
from app.utils.media import media_url


class RecommendationService:
    _model_bundle = None

    def __init__(self, db):
        self.db = db
        self.post_repo = PostRepository(db)
        self.scrap_repo = ScrapRepository(db)
        self.view_repo = PostViewRepository(db)
        self.user_repo = UserRepository(db)
        self.preprocessor = RecommendationPreprocessor()
        self.hybrid = HybridRecommender()
        self.stage3 = Stage3Recommender()

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

        if bundle is None:
            popular = sorted(posts, key=lambda item: item.get("view_count", 0), reverse=True)
            return {
                "destinations": [],
                "posts": self._attach_media(popular[:limit]),
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
            "model_ready": True,
            "stage3_ready": self._is_stage3_bundle(bundle),
            "ranking_weights": bundle.get("ranking_weights"),
        }

    def train_model(self):
        training_rows = self.post_repo.find_all_for_ml_training()
        scrap_rows = self.scrap_repo.find_all_for_ml_training()
        self.preprocessor.export_training_to_csv(training_rows, scrap_rows)
        bundle = self.preprocessor.train_random_forest()

        content_posts = self.post_repo.find_all_for_content_index()
        scrap_pairs = self.scrap_repo.find_all_pairs()
        artifacts = self.stage3.build_artifacts(content_posts, scrap_pairs)
        bundle["hybrid_artifacts"] = artifacts
        bundle["model_version"] = 4

        post_lookup = {post["post_id"]: post for post in content_posts}
        view_rows = self.view_repo.find_all_for_training()

        def feature_builder(user_id, post_id):
            user = self.user_repo.find_by_id(user_id)
            if not user:
                return None
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
            scrap_post_ids = self.scrap_repo.find_post_ids_by_user(user_id)
            own_post_ids = self.post_repo.find_post_ids_by_user(user_id)
            view_weights = self._view_weights_for_user(user_id, view_rows)
            return self.stage3.compute_feature_scores(
                artifacts,
                user_id,
                post_id,
                post_lookup,
                destinations,
                scrap_post_ids,
                own_post_ids,
                view_weights,
            )

        bundle["ranking_weights"] = self.stage3.train_ranking_weights(
            scrap_rows,
            content_posts,
            feature_builder,
        )

        metrics = self.preprocessor.evaluate_model_metrics(self.db)
        stage3_metrics = self._evaluate_stage3_ranking(bundle, scrap_rows, view_rows)
        rf_rank_metrics = self._evaluate_ranking_baseline(bundle, scrap_rows, mode="rf")
        if stage3_metrics:
            metrics["stage3_country_hit_at_3"] = stage3_metrics.get("country_hit_at_3")
            metrics["stage3_post_hit_at_3"] = stage3_metrics.get("post_hit_at_3")
            metrics["stage3_evaluated"] = stage3_metrics.get("evaluated")
        if rf_rank_metrics:
            metrics["rf_rank_country_hit_at_3"] = rf_rank_metrics.get("country_hit_at_3")

        bundle["metrics"] = metrics
        self.preprocessor.save_model_bundle(bundle)
        RecommendationService._model_bundle = bundle
        return {
            "trained_at": bundle.get("trained_at"),
            "sample_count": bundle.get("sample_count"),
            "metrics": metrics,
            "ranking_weights": bundle.get("ranking_weights"),
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
        stage3 = self._is_stage3_bundle(bundle)
        return {
            "exists": True,
            "trained_at": bundle.get("trained_at"),
            "sample_count": bundle.get("sample_count"),
            "model_version": bundle.get("model_version"),
            "top1_accuracy": metrics.get("top1_accuracy"),
            "top3_accuracy": metrics.get("top3_accuracy"),
            "feature_count": metrics.get("feature_count") or len(feature_columns),
            "hybrid_enabled": self._get_ranking_artifacts(bundle) is not None,
            "stage3_enabled": stage3,
            "ranking_weights": bundle.get("ranking_weights"),
            "stage3_country_hit_at_3": metrics.get("stage3_country_hit_at_3")
            or metrics.get("hybrid_country_hit_at_3"),
            "stage3_post_hit_at_3": metrics.get("stage3_post_hit_at_3")
            or metrics.get("hybrid_post_hit_at_3"),
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

    def _get_ranking_artifacts(self, bundle):
        return bundle.get("hybrid_artifacts") if bundle else None

    def _is_stage3_bundle(self, bundle):
        artifacts = self._get_ranking_artifacts(bundle)
        return bool(artifacts and "semantic_matrix" in artifacts)

    def _view_weights_for_user(self, user_id, view_rows=None):
        if view_rows is None:
            rows = self.view_repo.find_post_ids_by_user(user_id)
        else:
            rows = [row for row in view_rows if row["user_id"] == user_id]
        if not rows:
            return {}
        max_count = max(int(row.get("view_count") or 1) for row in rows)
        return {
            row["post_id"]: int(row.get("view_count") or 1) / max_count
            for row in rows
        }

    def _rank_posts(self, bundle, user_id, posts, destinations, scrap_stats, post_stats, limit):
        artifacts = self._get_ranking_artifacts(bundle)
        if not artifacts:
            return self.preprocessor.rank_posts_by_destinations(posts, destinations, limit=limit)

        scrap_post_ids = self.scrap_repo.find_post_ids_by_user(user_id)
        own_post_ids = self.post_repo.find_post_ids_by_user(user_id)
        view_weights = self._view_weights_for_user(user_id)
        ranking_weights = bundle.get("ranking_weights")

        if self._is_stage3_bundle(bundle):
            ranked = self.stage3.rank_posts(
                artifacts,
                user_id,
                posts,
                destinations,
                scrap_post_ids,
                own_post_ids,
                view_post_weights=view_weights,
                ranking_weights=ranking_weights,
                limit=limit,
            )
        else:
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

    def _evaluate_stage3_ranking(self, bundle, scrap_rows, view_rows):
        return self._evaluate_ranking_baseline(bundle, scrap_rows, mode="stage3", view_rows=view_rows)

    def _evaluate_ranking_baseline(self, bundle, scrap_rows, mode="stage3", view_rows=None):
        artifacts = self._get_ranking_artifacts(bundle)
        if mode == "stage3" and not artifacts:
            return None

        catalog_posts = self.post_repo.find_all_for_content_index()
        view_rows = view_rows or self.view_repo.find_all_for_training()
        evaluator = self.stage3 if self._is_stage3_bundle(bundle) else self.hybrid

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
            if mode == "rf":
                return self.preprocessor.rank_posts_by_destinations(
                    catalog_posts,
                    destinations,
                    limit=3,
                )
            if self._is_stage3_bundle(bundle):
                view_weights = self._view_weights_for_user(user_id, view_rows)
                return self.stage3.rank_posts(
                    artifacts,
                    user_id,
                    catalog_posts,
                    destinations,
                    scrap_post_ids,
                    own_post_ids,
                    view_post_weights=view_weights,
                    ranking_weights=bundle.get("ranking_weights"),
                    limit=3,
                )
            return self.hybrid.rank_posts(
                artifacts,
                user_id,
                catalog_posts,
                destinations,
                scrap_post_ids,
                own_post_ids,
                limit=3,
            )

        return evaluator.evaluate_recommendations(scrap_rows, rank_fn)

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
