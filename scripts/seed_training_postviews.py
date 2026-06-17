"""Seed realistic-ish PostViews, retrain model, and evaluate."""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from app import create_app
from app.db import get_db
from app.preprocessing.recommendation_preprocessor import RecommendationPreprocessor
from app.services.recommendation_service import RecommendationService
from app.services.service_factory import get_recommendation_service


def pct(value):
    if value is None:
        return "-"
    return f"{value * 100:.1f}%"


def seed_browsing_views(db, seed=2026):
    """Insert synthetic PostViews: prefer countries the user already interacted with."""
    random.seed(seed)
    with db.cursor() as cursor:
        cursor.execute("SELECT user_id FROM Users")
        user_ids = [row["user_id"] for row in cursor.fetchall()]

        cursor.execute("SELECT post_id, location_country FROM Posts")
        posts = cursor.fetchall()
        posts_by_country = {}
        all_post_ids = []
        for row in posts:
            all_post_ids.append(row["post_id"])
            posts_by_country.setdefault(row["location_country"], []).append(row["post_id"])

        cursor.execute(
            """
            SELECT s.user_id, p.location_country FROM Scraps s
            JOIN Posts p ON p.post_id = s.post_id
            """
        )
        scrap_countries = {}
        for row in cursor.fetchall():
            scrap_countries.setdefault(row["user_id"], []).append(row["location_country"])

        cursor.execute(
            """
            SELECT p.user_id, p.location_country FROM Posts p
            WHERE p.user_id IS NOT NULL
            """
        )
        for row in cursor.fetchall():
            scrap_countries.setdefault(row["user_id"], []).append(row["location_country"])

        cursor.execute("DELETE FROM PostViews")
        inserted = 0

        for user_id in user_ids:
            countries = scrap_countries.get(user_id, [])
            if not countries:
                if random.random() < 0.25:
                    targets = random.sample(all_post_ids, k=min(random.randint(2, 5), len(all_post_ids)))
                else:
                    continue
            else:
                preferred = list({c for c in countries})
                random.shuffle(preferred)
                top_countries = preferred[: min(3, len(preferred))]
                targets = []
                for _ in range(random.randint(4, 10)):
                    if random.random() < 0.75 and top_countries:
                        country = random.choice(top_countries)
                        pool = posts_by_country.get(country) or all_post_ids
                    else:
                        pool = all_post_ids
                    targets.append(random.choice(pool))
                if random.random() < 0.2:
                    targets.extend(
                        random.sample(all_post_ids, k=min(2, len(all_post_ids)))
                    )

            seen = set()
            for post_id in targets:
                key = (user_id, post_id)
                if key in seen:
                    continue
                seen.add(key)
                view_count = random.randint(1, 4)
                cursor.execute(
                    """
                    INSERT INTO PostViews (user_id, post_id, view_count, last_viewed_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON DUPLICATE KEY UPDATE view_count = view_count + %s
                    """,
                    (user_id, post_id, view_count, random.randint(0, 2)),
                )
                inserted += 1

    db.commit()
    with db.cursor() as cursor:
        cursor.execute("SELECT COUNT(*) AS n FROM PostViews")
        total = cursor.fetchone()["n"]
        cursor.execute("SELECT COUNT(DISTINCT user_id) AS n FROM PostViews")
        users = cursor.fetchone()["n"]
    return inserted, total, users


def full_report(svc, pre, db, label):
    bundle = svc._load_model()
    status = svc.get_model_status()
    fresh_rf = pre.evaluate_model_metrics(db)
    scrap_rows = svc.scrap_repo.find_all_for_ml_training()
    view_rows = svc.view_repo.find_all_for_training()
    stage3 = svc._evaluate_stage3_ranking(bundle, scrap_rows, view_rows) if bundle else None

    print(f"--- {label} ---")
    print(f"PostViews: {len(view_rows)}건")
    print(f"LTR: {status.get('ranking_weights')}")
    print(f"RF Top-1: {pct(fresh_rf.get('top1_accuracy'))}  Top-3: {pct(fresh_rf.get('top3_accuracy'))}")
    if stage3:
        print(
            f"랭킹 국가 Hit@3: {pct(stage3['country_hit_at_3'])}  "
            f"게시물 Hit@3: {pct(stage3['post_hit_at_3'])}  ({stage3['evaluated']}건)"
        )
    print()


def main():
    app = create_app()
    with app.app_context():
        db = get_db()
        pre = RecommendationPreprocessor()
        svc = get_recommendation_service()

        print("=== PostViews 학습용 데이터 삽입 + 재학습 ===\n")
        full_report(svc, pre, db, "삽입 전 (PostViews 0)")

        attempts, total, users = seed_browsing_views(db)
        print(f"삽입: {total}건 (시도 {attempts}, 활성 사용자 {users}명)\n")

        RecommendationService.refresh_model()
        svc = get_recommendation_service()
        full_report(svc, pre, db, "삽입 직후 (재학습 전)")

        print("모델 재학습 중...\n")
        result = svc.train_model()
        metrics = result.get("metrics") or {}
        print(f"학습 완료: {result.get('trained_at')}")
        print(f"LTR 가중치: {result.get('ranking_weights')}\n")

        full_report(svc, pre, db, "재학습 후")
        print("=== 저장된 번들 메트릭 ===")
        print(f"RF Top-1: {pct(metrics.get('top1_accuracy'))}")
        print(f"RF Top-3: {pct(metrics.get('top3_accuracy'))}")
        print(f"3단계 국가 Hit@3: {pct(metrics.get('stage3_country_hit_at_3'))}")
        print(f"3단계 게시물 Hit@3: {pct(metrics.get('stage3_post_hit_at_3'))}")
        print(f"RF-only 랭킹 Hit@3: {pct(metrics.get('rf_rank_country_hit_at_3'))}")


if __name__ == "__main__":
    main()
