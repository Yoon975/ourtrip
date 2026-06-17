"""기존 DB를 유지한 채 대량 샘플 데이터(~2000건)를 추가합니다."""
import random
import sys
from datetime import date, datetime, timedelta

import pymysql

ROOT = __import__("pathlib").Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Config

PASSWORD_HASH = (
    "scrypt:32768:8:1$gG2yoMMNqaeKYX0M$"
    "ed4ca646273ebeb8c9c83024fd8d1e42c80b208c41f8931fd1c23dcde78ff43d2e09b21e3d2ca04cfb9b4f5dde90d6cb92ba3e7e8a29b445737cfc00cf8a2ab6"
)

USER_COUNT = 150
POST_COUNT = 1400
SCRAP_COUNT = 250
COMMENT_COUNT = 200

DESTINATIONS = [
    ("대한민국", "서울"), ("대한민국", "부산"), ("대한민국", "제주"), ("대한민국", "강릉"),
    ("대한민국", "전주"), ("대한민국", "여수"), ("일본", "도쿄"), ("일본", "교토"),
    ("일본", "후쿠오카"), ("일본", "삿포로"), ("일본", "오사카"), ("태국", "방콕"),
    ("태국", "치앙마이"), ("태국", "푸켓"), ("베트남", "다낭"), ("베트남", "하노이"),
    ("베트남", "호치민"), ("프랑스", "파리"), ("프랑스", "니스"), ("스페인", "바르셀로나"),
    ("스페인", "마드리드"), ("이탈리아", "로마"), ("이탈리아", "밀라노"), ("미국", "뉴욕"),
    ("미국", "로스앤젤레스"), ("호주", "시드니"), ("호주", "멜bourne"), ("중국", "상하이"),
    ("중국", "베이징"), ("싱가포르", "싱가포르"), ("대만", "타이pei"), ("캐나다", "밴쿠버"),
    ("영국", "런don"), ("스위스", "취리히"), ("체코", "프라ha"), ("인도네시아", "발리"),
]

TITLES = ["{city} 2박 3일", "{city} 주말 여행", "{city} 감성 여행", "{city} 맛집 탐방"]
CONTENTS = [
    "{country} {city}에서 현지 음식과 명소를 돌아본 여행기입니다.",
    "짧은 일정으로 즐긴 {city} 여행. 이동 동선과 예산 팁을 정리했습니다.",
    "{city}의 카페, 골목, 포토스팟을 중심으로 기록한 여행 노트입니다.",
]
COMMENT_TEXTS = [
    "동선 참고했어요!", "사진 너무 예뻐요.", "맛집 리스트 저장!", "다음에 꼭 가볼게요.",
    "일정표 유용해요.", "교통 정보 감사합니다.", "현지 팁 도움됐어요.",
]


def _random_dt(rng, days_back=400):
    delta = timedelta(days=rng.randint(1, days_back), hours=rng.randint(8, 22))
    return datetime.now() - delta


def _travel_dates(rng):
    duration = rng.randint(1, 6)
    end = date.today() - timedelta(days=rng.randint(5, 500))
    start = end - timedelta(days=duration - 1)
    return start, end, duration


def main():
    rng = random.Random(20260616)
    conn = pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset=Config.DB_CHARSET,
    )

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT COALESCE(MAX(user_id), 0) FROM Users")
            start_user_id = cursor.fetchone()[0] + 1
            cursor.execute("SELECT user_id FROM Users")
            existing_user_ids = [row[0] for row in cursor.fetchall()]

            user_rows = []
            new_user_ids = []
            for i in range(USER_COUNT):
                user_id = start_user_id + i
                gender = "F" if i % 2 == 0 else "M"
                birth_year = 1988 + (i % 18)
                created_at = _random_dt(rng, 700)
                profile_path = f"uploads/profiles/user_{user_id}.jpg"
                user_rows.append(
                    (
                        user_id,
                        f"bulk{user_id}@ourtrip.com",
                        PASSWORD_HASH,
                        f"여행러{user_id}",
                        gender,
                        birth_year,
                        profile_path,
                        "user",
                        created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    )
                )
                new_user_ids.append(user_id)

            cursor.executemany(
                """
                INSERT INTO Users (
                    user_id, email, password, nickname, gender, birth_year,
                    profile_image_url, role, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                user_rows,
            )

            all_user_ids = existing_user_ids + new_user_ids
            post_rows = []
            image_rows = []
            post_ids = []

            for i in range(POST_COUNT):
                country, city = DESTINATIONS[i % len(DESTINATIONS)]
                user_id = rng.choice(all_user_ids)
                title = TITLES[i % len(TITLES)].format(city=city, country=country)
                content = CONTENTS[i % len(CONTENTS)].format(city=city, country=country)
                start, end, _ = _travel_dates(rng)
                created_at = _random_dt(rng, 500)
                view_count = rng.randint(10, 900)
                post_rows.append(
                    (
                        user_id,
                        title,
                        content,
                        country,
                        city,
                        start.isoformat(),
                        end.isoformat(),
                        view_count,
                        created_at.strftime("%Y-%m-%d %H:%M:%S"),
                    )
                )

            cursor.executemany(
                """
                INSERT INTO Posts (
                    user_id, title, content, location_country, location_city,
                    travel_start_date, travel_end_date, view_count, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                post_rows,
            )

            cursor.execute("SELECT post_id FROM Posts ORDER BY post_id DESC LIMIT %s", (POST_COUNT,))
            post_ids = [row[0] for row in reversed(cursor.fetchall())]

            for post_id in post_ids:
                image_rows.append((post_id, f"uploads/posts/post_{post_id}_main.jpg", 1))

            cursor.executemany(
                "INSERT INTO Post_Images (post_id, image_url, image_order) VALUES (%s, %s, %s)",
                image_rows,
            )

            scrap_pairs = set()
            scrap_rows = []
            while len(scrap_rows) < SCRAP_COUNT:
                user_id = rng.choice(all_user_ids)
                post_id = rng.choice(post_ids)
                pair = (user_id, post_id)
                if pair in scrap_pairs:
                    continue
                scrap_pairs.add(pair)
                scrap_rows.append((user_id, post_id, _random_dt(rng, 200).strftime("%Y-%m-%d %H:%M:%S")))

            cursor.executemany(
                "INSERT IGNORE INTO Scraps (user_id, post_id, created_at) VALUES (%s, %s, %s)",
                scrap_rows,
            )

            comment_rows = []
            for i in range(COMMENT_COUNT):
                comment_rows.append(
                    (
                        rng.choice(post_ids),
                        rng.choice(all_user_ids),
                        COMMENT_TEXTS[i % len(COMMENT_TEXTS)],
                        _random_dt(rng, 180).strftime("%Y-%m-%d %H:%M:%S"),
                    )
                )

            cursor.executemany(
                """
                INSERT INTO Comments (post_id, user_id, content, created_at)
                VALUES (%s, %s, %s, %s)
                """,
                comment_rows,
            )

            cursor.execute("SELECT COUNT(*) FROM Users")
            users = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Posts")
            posts = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Scraps")
            scraps = cursor.fetchone()[0]
            cursor.execute("SELECT COUNT(*) FROM Comments")
            comments = cursor.fetchone()[0]

        conn.commit()
        added = USER_COUNT + POST_COUNT + SCRAP_COUNT + COMMENT_COUNT
        print(f"대량 샘플 추가 완료: +{added}건")
        print(f"현재 DB: Users={users}, Posts={posts}, Scraps={scraps}, Comments={comments}")
    except Exception as exc:
        conn.rollback()
        print("대량 샘플 추가 실패:", exc)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
