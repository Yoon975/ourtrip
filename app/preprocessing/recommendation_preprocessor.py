import csv
from datetime import date, datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, top_k_accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

from app.config import Config


GENDER_CODE = {"M": 0, "F": 1, "U": 0}
SCRAP_WEIGHT = 2.0
POST_WEIGHT = 1.0
BASE_FEATURE_COLUMNS = ["age", "gender_code", "avg_duration", "avg_month"]


class RecommendationPreprocessor:
    """게시물·스크랩 CSV 변환 + Random Forest 여행지 추천 모델."""

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
            "travel_month",
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
            "travel_month": self._travel_month(row),
            "birth_year": birth_year or "",
            "age": age,
            "gender": gender,
            "gender_code": GENDER_CODE.get(gender, 0),
            "created_at": self._format_datetime(row.get("created_at")),
        }

    def evaluate_model_metrics(self, db):
        from app.repositories.post_repository import PostRepository
        from app.repositories.scrap_repository import ScrapRepository

        post_repo = PostRepository(db)
        scrap_repo = ScrapRepository(db)
        self.export_training_to_csv(
            post_repo.find_all_for_ml_training(),
            scrap_repo.find_all_for_ml_training(),
        )

        df = self._load_training_dataframe()
        if df.empty or df[self.TARGET_COLUMN].nunique() < 2:
            return {"sample_count": len(df), "top1_accuracy": None, "top3_accuracy": None}

        country_order = self._country_order_from_df(df)
        features = self.build_feature_matrix(df, country_order)
        labels = df[self.TARGET_COLUMN]
        label_encoder = LabelEncoder()
        encoded = label_encoder.fit_transform(labels)

        if len(df) < 20:
            model = self._create_model()
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

        model = self._create_model()
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
            "feature_count": len(features.columns),
        }

    def export_posts_to_csv(self, rows):
        return self.export_training_to_csv(rows, [])

    def train_random_forest(self, csv_path=None):
        csv_path = csv_path or Config.RECOMMENDATION_CSV
        df = self._load_training_dataframe(csv_path)

        fallback_countries = (
            df[self.TARGET_COLUMN].value_counts().index.tolist() if not df.empty else []
        )

        if len(df) < 5 or df[self.TARGET_COLUMN].nunique() < 2:
            bundle = self._empty_bundle(fallback_countries, len(df))
            self._save_model(bundle)
            return bundle

        country_order = self._country_order_from_df(df)
        feature_columns = self._feature_column_names(country_order)
        features = self.build_feature_matrix(df, country_order)
        labels = df[self.TARGET_COLUMN]
        label_encoder = LabelEncoder()
        encoded_labels = label_encoder.fit_transform(labels)

        model = self._create_model()
        model.fit(features, encoded_labels)

        bundle = {
            "model": model,
            "label_encoder": label_encoder,
            "feature_columns": feature_columns,
            "country_order": country_order,
            "fallback_countries": fallback_countries,
            "trained_at": datetime.now().isoformat(),
            "sample_count": len(df),
            "model_version": 2,
        }
        self._save_model(bundle)
        return bundle

    def save_model_bundle(self, bundle):
        self._save_model(bundle)

    def load_model_bundle(self):
        if not Config.RECOMMENDATION_MODEL.exists():
            return None
        bundle = joblib.load(Config.RECOMMENDATION_MODEL)
        if not bundle.get("country_order"):
            return None
        return bundle

    def predict_destinations(
        self,
        bundle,
        age,
        gender,
        scrap_stats=None,
        post_stats=None,
        top_k=3,
    ):
        if bundle is None:
            return []

        scrap_stats = scrap_stats or []
        post_stats = post_stats or []
        feature_row = self.build_user_feature_row(
            age=age,
            gender=gender,
            country_order=bundle.get("country_order", []),
            scrap_stats=scrap_stats,
            post_stats=post_stats,
        )
        feature_columns = bundle.get("feature_columns") or self._feature_column_names(
            bundle.get("country_order", [])
        )
        features = pd.DataFrame([feature_row], columns=feature_columns)

        model = bundle.get("model")
        label_encoder = bundle.get("label_encoder")

        if model is None or label_encoder is None:
            countries = self._history_fallback_countries(
                bundle.get("country_order", []),
                scrap_stats,
                post_stats,
                bundle.get("fallback_countries", []),
                top_k,
            )
            return [
                {"country": country, "probability": None}
                for country in countries
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

    def build_feature_matrix(self, df, country_order):
        rows = []
        country_index = {country: index for index, country in enumerate(country_order)}
        grouped = df.groupby("user_id", sort=False)

        for _, user_rows in grouped:
            user_rows = user_rows.sort_values(["created_at", "source_type", "source_id"])
            scrap_acc = [0.0] * len(country_order)
            post_acc = [0.0] * len(country_order)
            duration_vals = []
            month_vals = []

            for _, row in user_rows.iterrows():
                country_idx = country_index.get(row["location_country"])
                rows.append(
                    self._feature_row_from_state(
                        age=int(row["age"]),
                        gender_code=int(row["gender_code"]),
                        scrap_acc=scrap_acc,
                        post_acc=post_acc,
                        duration_vals=duration_vals,
                        month_vals=month_vals,
                        country_order=country_order,
                    )
                )

                if country_idx is None:
                    continue

                if row["source_type"] == "scrap":
                    scrap_acc[country_idx] += SCRAP_WEIGHT
                else:
                    post_acc[country_idx] += POST_WEIGHT

                duration = float(row.get("travel_duration_days") or 0)
                month = float(row.get("travel_month") or 0)
                if duration > 0:
                    duration_vals.append(duration)
                if month > 0:
                    month_vals.append(month)

        columns = self._feature_column_names(country_order)
        return pd.DataFrame(rows, columns=columns)

    def build_user_feature_row(self, age, gender, country_order, scrap_stats, post_stats):
        scrap_acc = [0.0] * len(country_order)
        post_acc = [0.0] * len(country_order)
        duration_vals = []
        month_vals = []
        country_index = {country: index for index, country in enumerate(country_order)}

        for stat in scrap_stats:
            country = stat.get("country")
            idx = country_index.get(country)
            if idx is None:
                continue
            count = int(stat.get("cnt") or 0)
            scrap_acc[idx] += count * SCRAP_WEIGHT
            self._append_travel_stats(stat, count, duration_vals, month_vals)

        for stat in post_stats:
            country = stat.get("country")
            idx = country_index.get(country)
            if idx is None:
                continue
            count = int(stat.get("cnt") or 0)
            post_acc[idx] += count * POST_WEIGHT
            self._append_travel_stats(stat, count, duration_vals, month_vals)

        return self._feature_row_from_state(
            age=int(age),
            gender_code=GENDER_CODE.get(gender or "U", 0),
            scrap_acc=scrap_acc,
            post_acc=post_acc,
            duration_vals=duration_vals,
            month_vals=month_vals,
            country_order=country_order,
        )

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

    def _load_training_dataframe(self, csv_path=None):
        csv_path = csv_path or Config.RECOMMENDATION_CSV
        df = pd.read_csv(csv_path)
        df = df.dropna(subset=[self.TARGET_COLUMN])
        df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(28).astype(int)
        df["gender_code"] = pd.to_numeric(df["gender_code"], errors="coerce").fillna(0).astype(int)
        df["travel_duration_days"] = pd.to_numeric(
            df.get("travel_duration_days", 0), errors="coerce"
        ).fillna(0)
        df["travel_month"] = pd.to_numeric(df.get("travel_month", 0), errors="coerce").fillna(0)
        if "created_at" in df.columns:
            df["created_at"] = pd.to_datetime(df["created_at"], errors="coerce")
        return df

    def _country_order_from_df(self, df):
        return sorted(df[self.TARGET_COLUMN].dropna().unique().tolist())

    def _feature_column_names(self, country_order):
        scrap_cols = [f"scrap_{index}" for index in range(len(country_order))]
        post_cols = [f"post_{index}" for index in range(len(country_order))]
        return BASE_FEATURE_COLUMNS[:2] + scrap_cols + post_cols + BASE_FEATURE_COLUMNS[2:]

    def _feature_row_from_state(
        self,
        age,
        gender_code,
        scrap_acc,
        post_acc,
        duration_vals,
        month_vals,
        country_order,
    ):
        row = {
            "age": age,
            "gender_code": gender_code,
            "avg_duration": round(sum(duration_vals) / len(duration_vals), 2) if duration_vals else 0.0,
            "avg_month": round(sum(month_vals) / len(month_vals), 2) if month_vals else 0.0,
        }
        for index in range(len(country_order)):
            row[f"scrap_{index}"] = scrap_acc[index]
            row[f"post_{index}"] = post_acc[index]
        return row

    def _append_travel_stats(self, stat, count, duration_vals, month_vals):
        if count <= 0:
            return
        if stat.get("avg_duration"):
            duration_vals.extend([float(stat["avg_duration"])] * count)
        if stat.get("avg_month"):
            month_vals.extend([float(stat["avg_month"])] * count)

    def _history_fallback_countries(self, country_order, scrap_stats, post_stats, fallback, top_k):
        scores = {country: 0.0 for country in country_order}
        for stat in scrap_stats:
            country = stat.get("country")
            if country in scores:
                scores[country] += float(stat.get("cnt") or 0) * SCRAP_WEIGHT
        for stat in post_stats:
            country = stat.get("country")
            if country in scores:
                scores[country] += float(stat.get("cnt") or 0) * POST_WEIGHT

        ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
        countries = [country for country, score in ranked if score > 0]
        if countries:
            return countries[:top_k]

        return list(fallback)[:top_k]

    def _create_model(self):
        return RandomForestClassifier(
            n_estimators=160,
            max_depth=12,
            random_state=42,
            class_weight="balanced",
        )

    def _empty_bundle(self, fallback_countries, sample_count):
        return {
            "model": None,
            "label_encoder": None,
            "feature_columns": BASE_FEATURE_COLUMNS,
            "country_order": [],
            "fallback_countries": fallback_countries,
            "trained_at": datetime.now().isoformat(),
            "sample_count": sample_count,
            "model_version": 2,
        }

    def _save_model(self, bundle):
        Config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(bundle, Config.RECOMMENDATION_MODEL)

    def _travel_duration(self, row):
        start = row.get("travel_start_date")
        end = row.get("travel_end_date")
        if not start or not end:
            return 0
        if isinstance(start, str):
            start = datetime.fromisoformat(str(start)).date()
        if isinstance(end, str):
            end = datetime.fromisoformat(str(end)).date()
        return max((end - start).days + 1, 0)

    def _travel_month(self, row):
        start = row.get("travel_start_date")
        if not start:
            return 0
        if isinstance(start, str):
            try:
                start = datetime.fromisoformat(str(start)).date()
            except ValueError:
                return 0
        return start.month if hasattr(start, "month") else 0

    def _format_datetime(self, value):
        if not value:
            return ""
        if isinstance(value, datetime):
            return value.strftime("%Y-%m-%d %H:%M:%S")
        return str(value)
