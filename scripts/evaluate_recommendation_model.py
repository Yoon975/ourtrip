"""Random Forest 추천 모델 정확도 평가."""
import sys
from pathlib import Path

import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, top_k_accuracy_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app
from app.config import Config
from app.db import get_db
from app.preprocessing.recommendation_preprocessor import RecommendationPreprocessor
from app.repositories.post_repository import PostRepository


def main():
    app = create_app()
    with app.app_context():
        rows = PostRepository(get_db()).find_all_for_ml_training()
        prep = RecommendationPreprocessor()
        prep.export_posts_to_csv(rows)
        df = pd.read_csv(Config.RECOMMENDATION_CSV)

        df["age"] = pd.to_numeric(df["age"], errors="coerce").fillna(28).astype(int)
        df["gender_code"] = pd.to_numeric(df["gender_code"], errors="coerce").fillna(0).astype(int)

        X = df[["age", "gender_code"]]
        y = df["location_country"]
        label_encoder = LabelEncoder()
        y_encoded = label_encoder.fit_transform(y)

        print("=== 데이터 개요 ===")
        print(f"학습 샘플 수: {len(df)}")
        print(f"여행지(국가) 클래스 수: {y.nunique()}")
        print(f"나이 범위: {df['age'].min()} ~ {df['age'].max()}")
        print(f"성별 분포: {df['gender'].value_counts().to_dict()}")
        print()
        print("국가별 게시글 수:")
        print(df["location_country"].value_counts().to_string())
        print()

        model = RandomForestClassifier(
            n_estimators=120,
            max_depth=8,
            random_state=42,
            class_weight="balanced",
        )

        class_counts = df["location_country"].value_counts()
        min_class = class_counts.min()
        n_splits = min(5, int(min_class), len(df))

        if n_splits >= 2 and y.nunique() >= 2:
            cv = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=42)
            cv_scores = cross_val_score(model, X, y_encoded, cv=cv, scoring="accuracy")
            print("=== 교차 검증 (Accuracy) ===")
            print(f"fold 수: {n_splits}")
            print(f"평균 정확도: {cv_scores.mean():.1%}")
            print(f"fold별: {[round(float(s), 3) for s in cv_scores]}")
        else:
            print("교차 검증: 샘플/클래스 수 부족으로 생략")

        if len(df) >= 10 and y.nunique() >= 2:
            X_train, X_test, y_train, y_test = train_test_split(
                X,
                y_encoded,
                test_size=0.25,
                random_state=42,
                stratify=y_encoded,
            )
            model.fit(X_train, y_train)
            y_pred = model.predict(X_test)

            print()
            print("=== Hold-out 테스트 (25%) ===")
            print(f"정확도 (Top-1): {accuracy_score(y_test, y_pred):.1%}")

            proba = model.predict_proba(X_test)
            n_classes = len(label_encoder.classes_)
            for k in [1, 3, 5]:
                k = min(k, n_classes)
                topk = top_k_accuracy_score(
                    y_test,
                    proba,
                    k=k,
                    labels=list(range(n_classes)),
                )
                print(f"Top-{k} 정확도: {topk:.1%}")

            print()
            print("=== 분류 리포트 (테스트) ===")
            print(
                classification_report(
                    y_test,
                    y_pred,
                    labels=list(range(len(label_encoder.classes_))),
                    target_names=label_encoder.classes_,
                    zero_division=0,
                )
            )

        model.fit(X, y_encoded)
        in_sample = accuracy_score(y_encoded, model.predict(X))
        random_baseline = 1.0 / y.nunique()

        print("=== 참고 지표 ===")
        print(f"In-sample 정확도: {in_sample:.1%} (과적합 참고용)")
        print(f"무작위 추측 기준선: {random_baseline:.1%} (클래스 {y.nunique()}개 균등)")


if __name__ == "__main__":
    main()
