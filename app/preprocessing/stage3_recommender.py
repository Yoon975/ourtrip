import random

import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import HashingVectorizer, TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import Normalizer
from scipy.sparse import csr_matrix

DEFAULT_WEIGHTS = {
    "rf": 0.28,
    "content": 0.32,
    "semantic": 0.15,
    "collab": 0.15,
    "view": 0.10,
}
COLD_WEIGHTS = {
    "rf": 0.45,
    "content": 0.20,
    "semantic": 0.15,
    "collab": 0.10,
    "view": 0.10,
}


class Stage3Recommender:
    """3단계: char-semantic 임베딩 + 조회 로그 + LTR 가중치 + 추천 설명."""

    def build_artifacts(self, posts, scrap_pairs):
        if not posts:
            return None

        post_ids = [post["post_id"] for post in posts]
        post_id_to_idx = {post_id: index for index, post_id in enumerate(post_ids)}
        documents = [self._document(post) for post in posts]

        tfidf_vectorizer = TfidfVectorizer(
            max_features=8000,
            min_df=1,
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        tfidf_matrix = tfidf_vectorizer.fit_transform(documents)

        char_vectorizer = HashingVectorizer(
            n_features=4096,
            analyzer="char_wb",
            ngram_range=(3, 5),
            alternate_sign=False,
        )
        char_matrix = char_vectorizer.transform(documents)
        svd = TruncatedSVD(n_components=128, random_state=42)
        semantic_matrix = Normalizer().fit_transform(svd.fit_transform(char_matrix))

        user_ids = sorted({pair["user_id"] for pair in scrap_pairs})
        collab_post_ids = sorted({pair["post_id"] for pair in scrap_pairs})
        user_to_idx = {user_id: index for index, user_id in enumerate(user_ids)}
        collab_post_to_idx = {post_id: index for index, post_id in enumerate(collab_post_ids)}

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
            "tfidf_vectorizer": tfidf_vectorizer,
            "tfidf_matrix": tfidf_matrix,
            "semantic_matrix": semantic_matrix,
            "post_ids": post_ids,
            "post_id_to_idx": post_id_to_idx,
            "collab_user_ids": user_ids,
            "collab_post_ids": collab_post_ids,
            "collab_matrix": collab_matrix,
        }

    def train_ranking_weights(self, scrap_rows, posts, feature_builder, sample_limit=400):
        if not scrap_rows or not posts:
            return DEFAULT_WEIGHTS.copy()

        post_ids = {post["post_id"] for post in posts}
        positives = scrap_rows[-sample_limit:]
        feature_names = ["rf", "content", "semantic", "collab", "view"]
        rows_x, rows_y = [], []

        for row in positives:
            user_id = row["user_id"]
            target_post_id = row["post_id"]
            features = feature_builder(user_id, target_post_id)
            if features:
                rows_x.append([features[name] for name in feature_names])
                rows_y.append(1)

            negatives = random.sample(
                list(post_ids - {target_post_id}),
                k=min(3, max(len(post_ids) - 1, 1)),
            )
            for negative_id in negatives:
                neg_features = feature_builder(user_id, negative_id)
                if neg_features:
                    rows_x.append([neg_features[name] for name in feature_names])
                    rows_y.append(0)

        if len(rows_x) < 20 or len(set(rows_y)) < 2:
            return DEFAULT_WEIGHTS.copy()

        model = LogisticRegression(max_iter=300, class_weight="balanced")
        model.fit(rows_x, rows_y)
        coefs = np.maximum(model.coef_[0], 0.0)
        if coefs.sum() <= 0:
            return DEFAULT_WEIGHTS.copy()

        normalized = coefs / coefs.sum()
        return {
            "rf": round(float(normalized[0]), 3),
            "content": round(float(normalized[1]), 3),
            "semantic": round(float(normalized[2]), 3),
            "collab": round(float(normalized[3]), 3),
            "view": round(float(normalized[4]), 3),
        }

    def rank_posts(
        self,
        artifacts,
        user_id,
        posts,
        destinations,
        scrap_post_ids,
        own_post_ids,
        view_post_weights=None,
        ranking_weights=None,
        limit=3,
    ):
        if not artifacts or not posts:
            return []

        view_post_weights = view_post_weights or {}
        weights = ranking_weights or DEFAULT_WEIGHTS
        country_scores = {item["country"]: item.get("probability") or 0.0 for item in destinations}
        max_country_score = max(country_scores.values()) if country_scores else 1.0
        if max_country_score <= 0:
            max_country_score = 1.0

        profile_ids = set(scrap_post_ids) | set(own_post_ids) | set(view_post_weights.keys())
        tfidf_profile = self._user_tfidf_profile(artifacts, profile_ids)
        semantic_profile = self._user_semantic_profile(artifacts, profile_ids)
        tfidf_similarities = self._similarities(artifacts["tfidf_matrix"], tfidf_profile)
        semantic_similarities = self._similarities(artifacts["semantic_matrix"], semantic_profile)
        collab_scores = self._collaborative_scores(artifacts, user_id)
        exclude_ids = set(own_post_ids)

        has_profile = bool(profile_ids)
        active_weights = weights if has_profile else COLD_WEIGHTS

        scored = []
        for post in posts:
            post_id = post.get("post_id")
            if post_id in exclude_ids:
                continue

            post_index = artifacts["post_id_to_idx"].get(post_id)
            country = post.get("location_country")
            rf_score = country_scores.get(country, 0.0) / max_country_score
            content_score = float(tfidf_similarities[post_index]) if post_index is not None and tfidf_similarities is not None else 0.0
            semantic_score = float(semantic_similarities[post_index]) if post_index is not None and semantic_similarities is not None else 0.0
            collab_score = collab_scores.get(post_id, 0.0)
            view_score = min(float(view_post_weights.get(post_id, 0.0)), 1.0)
            popularity = min(post.get("view_count", 0) / 1000, 0.12)

            final_score = (
                active_weights["rf"] * rf_score
                + active_weights["content"] * content_score
                + active_weights["semantic"] * semantic_score
                + active_weights["collab"] * collab_score
                + active_weights["view"] * view_score
                + popularity
            )
            scored.append(
                {
                    **post,
                    "recommendation_score": round(final_score, 4),
                    "score_rf": round(rf_score, 4),
                    "score_content": round(content_score, 4),
                    "score_semantic": round(semantic_score, 4),
                    "score_collab": round(collab_score, 4),
                    "score_view": round(view_score, 4),
                    "recommendation_reason": self._build_reason(
                        rf_score,
                        content_score,
                        semantic_score,
                        collab_score,
                        view_score,
                        country,
                    ),
                }
            )

        scored.sort(
            key=lambda item: (item["recommendation_score"], item.get("view_count", 0)),
            reverse=True,
        )
        return scored[:limit]

    def compute_feature_scores(
        self,
        artifacts,
        user_id,
        post_id,
        post_lookup,
        destinations,
        scrap_post_ids,
        own_post_ids,
        view_post_weights=None,
    ):
        post = post_lookup.get(post_id)
        post_index = artifacts["post_id_to_idx"].get(post_id)
        if not post or post_index is None:
            return None

        view_post_weights = view_post_weights or {}
        country_scores = {item["country"]: item.get("probability") or 0.0 for item in destinations}
        max_country_score = max(country_scores.values()) if country_scores else 1.0
        if max_country_score <= 0:
            max_country_score = 1.0

        profile_ids = set(scrap_post_ids) | set(own_post_ids) | set(view_post_weights.keys())
        tfidf_profile = self._user_tfidf_profile(artifacts, profile_ids)
        semantic_profile = self._user_semantic_profile(artifacts, profile_ids)
        tfidf_similarities = self._similarities(artifacts["tfidf_matrix"], tfidf_profile)
        semantic_similarities = self._similarities(artifacts["semantic_matrix"], semantic_profile)
        collab_scores = self._collaborative_scores(artifacts, user_id)

        country = post.get("location_country")
        rf_score = country_scores.get(country, 0.0) / max_country_score
        content_score = float(tfidf_similarities[post_index]) if tfidf_similarities is not None else 0.0
        semantic_score = float(semantic_similarities[post_index]) if semantic_similarities is not None else 0.0
        collab_score = collab_scores.get(post_id, 0.0)
        view_score = min(float(view_post_weights.get(post_id, 0.0)), 1.0)

        return {
            "rf": rf_score,
            "content": content_score,
            "semantic": semantic_score,
            "collab": collab_score,
            "view": view_score,
        }

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

            recommended = rank_fn(user_id, scrap_ids, set())
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

    def _document(self, post):
        city = post.get("location_city") or ""
        return " ".join(
            [
                str(post.get("title") or ""),
                str(post.get("content") or ""),
                str(post.get("location_country") or ""),
                str(city),
            ]
        )

    def _user_tfidf_profile(self, artifacts, post_ids):
        indices = [
            artifacts["post_id_to_idx"][post_id]
            for post_id in post_ids
            if post_id in artifacts["post_id_to_idx"]
        ]
        if not indices:
            return None
        return artifacts["tfidf_matrix"][indices].mean(axis=0)

    def _user_semantic_profile(self, artifacts, post_ids):
        indices = [
            artifacts["post_id_to_idx"][post_id]
            for post_id in post_ids
            if post_id in artifacts["post_id_to_idx"]
        ]
        if not indices:
            return None
        return artifacts["semantic_matrix"][indices].mean(axis=0)

    def _similarities(self, matrix, profile):
        if profile is None:
            return None
        if hasattr(profile, "toarray"):
            profile_array = np.asarray(profile.toarray(), dtype=float).reshape(1, -1)
        else:
            profile_array = np.asarray(profile, dtype=float).reshape(1, -1)
        return np.maximum(cosine_similarity(profile_array, matrix).flatten(), 0.0)

    def _collaborative_scores(self, artifacts, user_id):
        user_to_idx = {uid: index for index, uid in enumerate(artifacts["collab_user_ids"])}
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

    def _build_reason(self, rf_score, content_score, semantic_score, collab_score, view_score, country):
        parts = []
        if view_score >= 0.25:
            parts.append("최근 본 글과 비슷한 주제")
        if content_score >= 0.20 or semantic_score >= 0.20:
            parts.append("스크랩·작성 글과 유사한 콘텐츠")
        if collab_score >= 0.20:
            parts.append("비슷한 취향 사용자의 선택")
        if rf_score >= 0.20 and country:
            parts.append(f"{country} 여행 선호 예측")
        if not parts:
            parts.append("인기도와 여행지 적합도를 반영")
        return " · ".join(parts[:2])

    def _scrap_ids_for_user(self, scrap_rows, user_id):
        return {row["post_id"] for row in scrap_rows if row["user_id"] == user_id}
