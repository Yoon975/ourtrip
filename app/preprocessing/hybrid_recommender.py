from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from scipy.sparse import csr_matrix
import numpy as np

WEIGHT_RF = 0.35
WEIGHT_CONTENT = 0.45
WEIGHT_COLLAB = 0.20
WEIGHT_RF_COLD = 0.55
WEIGHT_CONTENT_COLD = 0.25
WEIGHT_COLLAB_COLD = 0.20


class HybridRecommender:
    """TF-IDF 콘텐츠 유사도 + 스크랩 협업 필터링 하이브리드 랭킹."""

    def build_artifacts(self, posts, scrap_pairs):
        if not posts:
            return None

        post_ids = [post["post_id"] for post in posts]
        post_id_to_idx = {post_id: index for index, post_id in enumerate(post_ids)}
        documents = []
        for post in posts:
            city = post.get("location_city") or ""
            documents.append(
                " ".join(
                    [
                        str(post.get("title") or ""),
                        str(post.get("content") or ""),
                        str(post.get("location_country") or ""),
                        str(city),
                    ]
                )
            )

        vectorizer = TfidfVectorizer(
            max_features=8000,
            min_df=1,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        tfidf_matrix = vectorizer.fit_transform(documents)

        user_ids = sorted({pair["user_id"] for pair in scrap_pairs})
        collab_post_ids = sorted({pair["post_id"] for pair in scrap_pairs})
        user_to_idx = {user_id: index for index, user_id in enumerate(user_ids)}
        collab_post_to_idx = {
            post_id: index for index, post_id in enumerate(collab_post_ids)
        }

        rows, cols, data = [], [], []
        for pair in scrap_pairs:
            user_index = user_to_idx.get(pair["user_id"])
            post_index = collab_post_to_idx.get(pair["post_id"])
            if user_index is None or post_index is None:
                continue
            rows.append(user_index)
            cols.append(post_index)
            data.append(1.0)

        collab_matrix = csr_matrix(
            (data, (rows, cols)),
            shape=(len(user_ids), len(collab_post_ids)),
        )

        return {
            "vectorizer": vectorizer,
            "tfidf_matrix": tfidf_matrix,
            "post_ids": post_ids,
            "post_id_to_idx": post_id_to_idx,
            "collab_user_ids": user_ids,
            "collab_post_ids": collab_post_ids,
            "collab_matrix": collab_matrix,
        }

    def rank_posts(
        self,
        artifacts,
        user_id,
        posts,
        destinations,
        scrap_post_ids,
        own_post_ids,
        limit=3,
    ):
        if not artifacts or not posts:
            return []

        country_scores = {
            item["country"]: item.get("probability") or 0.0 for item in destinations
        }
        max_country_score = max(country_scores.values()) if country_scores else 1.0
        if max_country_score <= 0:
            max_country_score = 1.0

        profile_ids = set(scrap_post_ids) | set(own_post_ids)
        content_profile = self._user_content_profile(artifacts, profile_ids)
        content_similarities = self._content_similarities(artifacts, content_profile)
        collab_scores = self._collaborative_scores(artifacts, user_id)
        exclude_ids = set(own_post_ids)

        has_profile = bool(profile_ids)
        weight_rf = WEIGHT_RF_COLD if not has_profile else WEIGHT_RF
        weight_content = WEIGHT_CONTENT_COLD if not has_profile else WEIGHT_CONTENT
        weight_collab = WEIGHT_COLLAB_COLD if not has_profile else WEIGHT_COLLAB

        scored = []
        for post in posts:
            post_id = post.get("post_id")
            if post_id in exclude_ids:
                continue

            country = post.get("location_country")
            rf_score = country_scores.get(country, 0.0) / max_country_score
            post_index = artifacts["post_id_to_idx"].get(post_id)
            content_score = (
                float(content_similarities[post_index])
                if post_index is not None and content_similarities is not None
                else 0.0
            )
            collab_score = collab_scores.get(post_id, 0.0)
            popularity = min(post.get("view_count", 0) / 1000, 0.15)

            final_score = (
                weight_rf * rf_score
                + weight_content * content_score
                + weight_collab * collab_score
                + popularity
            )
            scored.append(
                {
                    **post,
                    "recommendation_score": round(final_score, 4),
                    "score_rf": round(rf_score, 4),
                    "score_content": round(content_score, 4),
                    "score_collab": round(collab_score, 4),
                }
            )

        scored.sort(
            key=lambda item: (item["recommendation_score"], item.get("view_count", 0)),
            reverse=True,
        )
        return scored[:limit]

    def evaluate_recommendations(self, scrap_rows, rank_fn, sample_limit=80):
        if not scrap_rows:
            return None

        test_rows = scrap_rows[-sample_limit:]
        country_hits = 0
        post_hits = 0
        evaluated = 0

        for row in test_rows:
            user_id = row["user_id"]
            target_post_id = row["post_id"]
            target_country = row["location_country"]
            scrap_ids = self._scrap_ids_for_user(scrap_rows, user_id) - {target_post_id}
            own_ids = set()

            recommended = rank_fn(user_id, scrap_ids, own_ids)
            if not recommended:
                continue

            evaluated += 1
            countries = {post.get("location_country") for post in recommended}
            post_ids = {post.get("post_id") for post in recommended}
            if target_country in countries:
                country_hits += 1
            if target_post_id in post_ids:
                post_hits += 1

        if evaluated == 0:
            return None

        return {
            "evaluated": evaluated,
            "country_hit_at_3": round(country_hits / evaluated, 3),
            "post_hit_at_3": round(post_hits / evaluated, 3),
        }

    def _user_content_profile(self, artifacts, post_ids):
        indices = [
            artifacts["post_id_to_idx"][post_id]
            for post_id in post_ids
            if post_id in artifacts["post_id_to_idx"]
        ]
        if not indices:
            return None
        vectors = artifacts["tfidf_matrix"][indices]
        return vectors.mean(axis=0)

    def _content_similarities(self, artifacts, profile):
        if profile is None:
            return None
        profile_array = np.asarray(profile, dtype=float).reshape(1, -1)
        similarities = cosine_similarity(profile_array, artifacts["tfidf_matrix"]).flatten()
        return np.maximum(similarities, 0.0)

    def _collaborative_scores(self, artifacts, user_id):
        user_to_idx = {
            uid: index for index, uid in enumerate(artifacts["collab_user_ids"])
        }
        user_index = user_to_idx.get(user_id)
        if user_index is None:
            return {}

        matrix = artifacts["collab_matrix"]
        if matrix[user_index].nnz == 0:
            return {}

        similarities = cosine_similarity(matrix[user_index], matrix).flatten()
        similarities[user_index] = 0.0
        scores = similarities @ matrix
        max_score = float(scores.max()) if scores.max() > 0 else 1.0

        return {
            post_id: float(scores[index] / max_score)
            for index, post_id in enumerate(artifacts["collab_post_ids"])
        }

    def _scrap_ids_for_user(self, scrap_rows, user_id):
        return {
            row["post_id"]
            for row in scrap_rows
            if row["user_id"] == user_id
        }
