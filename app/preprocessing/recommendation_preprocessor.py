import csv
from datetime import date, datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder

from app.config import Config


GENDER_CODE = {"M": 0, "F": 1, "U": 0}


class RecommendationPreprocessor:
    """게시물 CSV 변환 + Random Forest 여행지 추천 모델."""

    FEATURE_COLUMNS = ["age", "gender_code"]
    TARGET_COLUMN = "location_country"

    def export_training_to_csv(self, post_rows, scrap_rows):
        Config.DATA_DIR.mkdir(parents=True, exist_ok=True)
        current_year = date.today().year

        fieldnames = [
            "source_type",
            "source_id",
            "user_id",
            "nickname",
            "location_country",
            "location_city",
            "view_count",
            "travel_duration_days",
            "birth_year",
            "age",
            "gender",
            "gender_code",
            "created_at",
        ]

        with Config.RECOMMENDATION_CSV.open("w", encoding="utf-8-sig", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            for row in post_rows:
                writer.writerow(self._training_row(row, "post", row["post_id"], current_year))

            for row in scrap_rows:
                writer.writerow(self._training_row(row, "scrap", row["scrap_id"], current_year))

        return Config.RECOMMENDATION_CSV

    def _training_row(self, row, source_type, source_id, current_year):
        birth_year = row.get("birth_year")
        age = current_year - int(birth_year) if birth_year else 28
        gender = row.get("gender") or "U"
        return {
            "source_type": source_type,
            "source_id": source_id,
            "user_id": row.get("user_id"),
            "nickname": row.get("nickname", ""),
            "location_country": row["location_country"],
            "location_city": row.get("location_city") or "",
            "view_count": row.get("view_count") or 0,
            "travel_duration_days": self._travel_duration(row),
            "birth_year": birth_year or "",
            "age": age,
            "gender": gender,
            "gender_code": GENDER_CODE.get(gender, 0),
            "created_at": self._format_datetime(row.get("created_at")),
        }

    def evaluate_model_metrics(self, db):
        from app.repositories.post_repository import PostRepository
        from app.repositories.scrap_repository import ScrapRepository
        from sklearn.metrics import accuracy_score, top_k_accuracy_score
        from sklearn.model_selection import train_test_split

        post_repo = PostRepository(db)
        scrap_repo = ScrapRepository(db)
        self.export_training_to_csv(
            post_repo.find_all_for_ml_training(),
            scrap_repo.find_all_for_ml_training(),
        )

        df = pd.read_csv(Config.RECOMMENDATION_CSV)
        if df.empty or df["location_country"].nunique() < 2:
            return {"sample_count": len(df), "top1_accuracy": None, "top3_accuracy": None}

        df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(28).astype(int)
        df["gender_code"] = pd.to_numeric(df["gender_code"], errors="coerce").fillna(0).astype(int)
        features = df[self.FEATURE_COLUMNS]
        labels = df[self.TARGET_COLUMN]
        label_encoder = LabelEncoder()
        encoded = label_encoder.fit_transform(labels)

        if len(df) < 20:
            model = RandomForestClassifier(n_estimators=120, max_depth=8, random_state=42, class_weight="balanced")
            model.fit(features, encoded)
            in_sample = accuracy_score(encoded, model.predict(features))
            return {
                "sample_count": len(df),
                "top1_accuracy": round(float(in_sample), 3),
                "top3_accuracy": None,
                "note": "샘플 수가 적어 in-sample 기준입니다.",
            }

        try:
            X_train, X_test, y_train, y_test = train_test_split(
                features, encoded, test_size=0.2, random_state=42, stratify=encoded
            )
        except ValueError:
            X_train, X_test, y_train, y_test = train_test_split(
                features, encoded, test_size=0.2, random_state=42
            )
        model = RandomForestClassifier(n_estimators=120, max_depth=8, random_state=42, class_weight="balanced")
        model.fit(X_train, y_train)
        y_pred = model.predict(X_test)
        proba = model.predict_proba(X_test)
        n_classes = len(label_encoder.classes_)
        top3 = top_k_accuracy_score(
            y_test, proba, k=min(3, n_classes), labels=list(range(n_classes))
        )
        return {
            "sample_count": len(df),
            "top1_accuracy": round(float(accuracy_score(y_test, y_pred)), 3),
            "top3_accuracy": round(float(top3), 3),
        }

    def export_posts_to_csv(self, rows):
        return self.export_training_to_csv(rows, [])

    def train_random_forest(self, csv_path=None):
        csv_path = csv_path or Config.RECOMMENDATION_CSV
        df = pd.read_csv(csv_path)

        df = df.dropna(subset=[self.TARGET_COLUMN])
        df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(28).astype(int)
        df["gender_code"] = pd.to_numeric(df["gender_code"], errors="coerce").fillna(0).astype(int)

        fallback_countries = (
            df[self.TARGET_COLUMN].value_counts().index.tolist() if not df.empty else []
        )

        if len(df) < 5 or df[self.TARGET_COLUMN].nunique() < 2:
            bundle = {
                "model": None,
                "label_encoder": None,
                "feature_columns": self.FEATURE_COLUMNS,
                "fallback_countries": fallback_countries,
                "trained_at": datetime.now().isoformat(),
                "sample_count": len(df),
            }
            self._save_model(bundle)
            return bundle

        features = df[self.FEATURE_COLUMNS]
        labels = df[self.TARGET_COLUMN]
        label_encoder = LabelEncoder()
        encoded_labels = label_encoder.fit_transform(labels)

        model = RandomForestClassifier(
            n_estimators=120,
            max_depth=8,
            random_state=42,
            class_weight="balanced",
        )
        model.fit(features, encoded_labels)

        bundle = {
            "model": model,
            "label_encoder": label_encoder,
            "feature_columns": self.FEATURE_COLUMNS,
            "fallback_countries": fallback_countries,
            "trained_at": datetime.now().isoformat(),
            "sample_count": len(df),
        }
        self._save_model(bundle)
        return bundle

    def load_model_bundle(self):
        if not Config.RECOMMENDATION_MODEL.exists():
            return None
        return joblib.load(Config.RECOMMENDATION_MODEL)

    def predict_destinations(self, bundle, age, gender, top_k=3):
        if bundle is None:
            return []

        gender_code = GENDER_CODE.get(gender or "U", 0)
        features = pd.DataFrame([[int(age), gender_code]], columns=self.FEATURE_COLUMNS)

        model = bundle.get("model")
        label_encoder = bundle.get("label_encoder")

        if model is None or label_encoder is None:
            countries = bundle.get("fallback_countries", [])
            return [
                {"country": country, "probability": None}
                for country in countries[:top_k]
            ]

        probabilities = model.predict_proba(features)[0]
        classes = label_encoder.classes_
        ranked = sorted(
            zip(classes, probabilities),
            key=lambda item: item[1],
            reverse=True,
        )

        return [
            {"country": country, "probability": round(float(prob), 3)}
            for country, prob in ranked[:top_k]
        ]

    def rank_posts_by_destinations(self, posts, destinations, limit=3):
        if not posts:
            return []

        country_scores = {
            item["country"]: item.get("probability") or 0.0 for item in destinations
        }
        if not country_scores:
            return posts[:limit]

        scored = []
        for post in posts:
            country = post.get("location_country")
            score = country_scores.get(country, 0.0)
            score += min(post.get("view_count", 0) / 1000, 0.2)
            scored.append({**post, "recommendation_score": round(score, 4)})

        scored.sort(
            key=lambda item: (item["recommendation_score"], item.get("view_count", 0)),
            reverse=True,
        )
        return scored[:limit]

    def user_age(self, birth_year):
        if not birth_year:
            return 28
        return max(date.today().year - int(birth_year), 1)

    def _save_model(self, bundle):
        Config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(bundle, Config.RECOMMENDATION_MODEL)

    def _travel_duration(self, post):
        start = post.get("travel_start_date")
        end = post.get("travel_end_date")
        if not start or not end:
            return 0
        if isinstance(start, str):
            start = datetime.fromisoformat(start).date()
        if isinstance(end, str):
            end = datetime.fromisoformat(end).date()
        return max((end - start).days + 1, 0)

    def _format_datetime(self, value):
        if not value:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value)
