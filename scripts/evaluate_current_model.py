"""Evaluate current recommendation model metrics."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import create_app
from app.preprocessing.recommendation_preprocessor import RecommendationPreprocessor
from app.services.service_factory import get_recommendation_service
from app.db import get_db


def pct(value):
    if value is None:
        return "—"
    return f"{value * 100:.1f}%"


def main():
    app = create_app()
    with app.app_context():
        svc = get_recommendation_service()
        pre = RecommendationPreprocessor()
        bundle = svc._load_model()
        db = get_db()

        status = svc.get_model_status()
        fresh_rf = pre.evaluate_model_metrics(db)

        scrap_rows = svc.scrap_repo.find_all_for_ml_training()
        training_rows = svc.post_repo.find_all_for_ml_training()
        view_rows = svc.view_repo.find_all_for_training()
        posts = svc.post_repo.find_all_for_content_index()

        stage3 = svc._evaluate_stage3_ranking(bundle, scrap_rows, view_rows) if bundle else None
        rf_rank = svc._evaluate_ranking_baseline(bundle, scrap_rows, mode="rf") if bundle else None

        print("=== 저장된 모델 ===")
        print(f"상태: {'저장됨' if status.get('exists') else '미생성'}")
        print(f"버전: v{status.get('model_version', '—')}")
        print(f"학습 시각: {status.get('trained_at') or '—'}")
        print(f"학습 샘플: {status.get('sample_count') or '—'}건")
        print(f"LTR 가중치: {status.get('ranking_weights') or '—'}")
        print()

        print("=== 저장 시점 메트릭 (모델 번들) ===")
        print(f"RF Top-1: {pct(status.get('top1_accuracy'))}")
        print(f"RF Top-3: {pct(status.get('top3_accuracy'))}")
        print(f"피처 수: {status.get('feature_count') or '—'}")
        print(f"3단계 국가 Hit@3: {pct(status.get('stage3_country_hit_at_3'))}")
        print(f"3단계 게시물 Hit@3: {pct(status.get('stage3_post_hit_at_3'))}")
        print(f"RF-only 랭킹 국가 Hit@3: {pct(status.get('rf_rank_country_hit_at_3'))}")
        print()

        print("=== 현재 DB 기준 재평가 (RF hold-out 20%) ===")
        print(f"샘플 수: {fresh_rf.get('sample_count')}건")
        print(f"피처 수: {fresh_rf.get('feature_count') or '—'}")
        print(f"RF Top-1: {pct(fresh_rf.get('top1_accuracy'))}")
        print(f"RF Top-3: {pct(fresh_rf.get('top3_accuracy'))}")
        if fresh_rf.get("note"):
            print(f"참고: {fresh_rf['note']}")
        print()

        print("=== 게시글 랭킹 재평가 (스크랩 hold-out, 최대 80건) ===")
        if stage3:
            print(
                f"3단계 국가 Hit@3: {pct(stage3['country_hit_at_3'])} "
                f"({stage3['evaluated']}건 평가)"
            )
            print(f"3단계 게시물 Hit@3: {pct(stage3['post_hit_at_3'])}")
        else:
            print("3단계: 모델 없음 또는 평가 불가")
        if rf_rank:
            print(f"RF-only 국가 Hit@3: {pct(rf_rank['country_hit_at_3'])}")
        print()

        print("=== 데이터 규모 ===")
        print(f"ML 학습 행 (게시글+스크랩): {len(training_rows) + len(scrap_rows)}건")
        print(f"  · 게시글: {len(training_rows)}건")
        print(f"  · 스크랩: {len(scrap_rows)}건")
        print(f"콘텐츠 인덱스 게시글: {len(posts)}건")
        print(f"PostViews 기록: {len(view_rows)}건")


if __name__ == "__main__":
    main()
