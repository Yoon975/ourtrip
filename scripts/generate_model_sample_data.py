# """모델 학습/전처리용 임의 샘플 데이터(테이블당 50건)를 SQL/JSON으로 생성합니다."""
# import json
# import pathlib
# import random
# from datetime import date, datetime, timedelta

# ROOT = pathlib.Path(__file__).resolve().parent.parent
# OUT_SQL = ROOT / "database" / "model_sample_data.sql"
# OUT_JSON = ROOT / "database" / "model_sample_data.json"

# SAMPLE_COUNT = 50
# PASSWORD_HASH = (
#     "scrypt:32768:8:1$gG2yoMMNqaeKYX0M$"
#     "ed4ca646273ebeb8c9c83024fd8d1e42c80b208c41f8931fd1c23dcde78ff43d2e09b21e3d2ca04cfb9b4f5dde90d6cb92ba3e7e8a29b445737cfc00cf8a2ab6"
# )

# NICKNAME_POOL = [
#     "해린", "준서", "나연", "도윤", "서연", "민재", "지후", "수빈", "예준", "하은",
#     "시우", "지아", "유진", "태민", "소율", "건우", "다은", "현우", "서윤", "지훈",
#     "은서", "승현", "채원", "동현", "가은", "민준", "수아", "재윤", "윤서", "지원",
#     "하준", "서현", "우진", "예나", "시윤", "지안", "민서", "준혁", "유나", "성민",
#     "지유", "현서", "태양", "수연", "재민", "소연", "영준", "혜원", "승우", "아린",
# ]

# DESTINATIONS = [
#     ("일본", "도쿄"), ("일본", "교토"), ("일본", "후쿠오카"), ("일본", "삿포로"), ("일본", "나고야"),
#     ("태국", "방콕"), ("태국", "치앙마이"), ("베트남", "다낭"), ("베트남", "하노이"), ("베트남", "호치민"),
#     ("프랑스", "파리"), ("프랑스", "니스"), ("스페인", "바르셀로나"), ("스페인", "마드리드"),
#     ("이탈리아", "로마"), ("이탈리아", "밀라노"), ("미국", "뉴욕"), ("미국", "로스앤젤레스"),
#     ("호주", "시드니"), ("호주", "멜bourne"), ("대한민국", "서울"), ("대한민국", "강릉"),
#     ("대한민국", "전주"), ("대한민국", "여수"), ("대한민국", "부산"), ("대한민국", "제주"),
#     ("중국", "상하이"), ("중국", "베이징"), ("싱가포르", "싱가포르"), ("대만", "타이pei"),
# ]

# TRIP_TEMPLATES = [
#     "{city} 2박 3일", "{city} 주말 여행", "{city} 감성 여행", "{city} 맛집 탐방", "{city} 야경 코스",
# ]

# CONTENT_TEMPLATES = [
#     "{country} {city}에서 현지 음식과 명소를 돌아본 여행기입니다.",
#     "짧은 일정으로 즐긴 {city} 여행. 이동 동선과 예산 팁을 정리했습니다.",
#     "{city}의 카페, 골목, 포토스팟을 중심으로 기록한 여행 노트입니다.",
#     "{city} 현지 맛집과 시장 투어 후기. 추천 메뉴와 대기 시간 정보 포함.",
#     "{city}에서의 하루 일정과 교통 패스 활용법을 공유합니다.",
# ]

# COMMENT_SAMPLES = [
#     "동선 참고해서 계획 세웠어요!", "사진 너무 예뻐요.", "맛집 리스트 저장했습니다.",
#     "다음 여행 때 꼭 가볼게요.", "일정표가 정말 유용해요.", "교통 정보 감사합니다.",
#     "현지 팁이 도움이 됐어요.", "추천 코스 따라 다녀왔어요.", "정말 도움 되는 글이에요.",
#     "사진 구도가 너무 좋아요.", "예산 정리가 특히 유용했어요.", "현지 교통 팁 최고예요.",
# ]


# def _sql_str(value):
#     if value is None:
#         return "NULL"
#     return "'" + str(value).replace("'", "''") + "'"


# def _random_created_at(rng, base_days_ago=180):
#     days = rng.randint(1, base_days_ago)
#     hours = rng.randint(8, 22)
#     minutes = rng.randint(0, 59)
#     return datetime.now() - timedelta(days=days, hours=hours, minutes=minutes)


# def build_dataset(seed=42):
#     rng = random.Random(seed)
#     users = []
#     posts = []
#     scraps = []
#     comments = []

#     for i in range(SAMPLE_COUNT):
#         user_id = 5 + i
#         users.append(
#             {
#                 "user_id": user_id,
#                 "email": f"sample{i + 1:02d}@ourtrip.com",
#                 "password": PASSWORD_HASH,
#                 "nickname": f"{NICKNAME_POOL[i % len(NICKNAME_POOL)]}{i + 1:02d}",
#                 "gender": "F" if i % 2 == 0 else "M",
#                 "birth_year": 1990 + (i % 13),
#                 "profile_image_url": None,
#                 "role": "user",
#                 "created_at": _random_created_at(rng, 300).strftime("%Y-%m-%d %H:%M:%S"),
#             }
#         )

#     all_user_ids = list(range(1, 5 + SAMPLE_COUNT))
#     destinations = list(DESTINATIONS)
#     rng.shuffle(destinations)

#     for i in range(SAMPLE_COUNT):
#         post_id = 5 + i
#         country, city = destinations[i % len(destinations)]
#         user_id = rng.choice(all_user_ids)
#         title = TRIP_TEMPLATES[i % len(TRIP_TEMPLATES)].format(city=city, country=country)
#         content = CONTENT_TEMPLATES[i % len(CONTENT_TEMPLATES)].format(city=city, country=country)
#         duration = rng.randint(1, 5)
#         end_date = date.today() - timedelta(days=rng.randint(10, 200))
#         start_date = end_date - timedelta(days=duration - 1)

#         posts.append(
#             {
#                 "post_id": post_id,
#                 "user_id": user_id,
#                 "title": title,
#                 "content": content,
#                 "location_country": country,
#                 "location_city": city,
#                 "travel_start_date": start_date.isoformat(),
#                 "travel_end_date": end_date.isoformat(),
#                 "view_count": rng.randint(20, 500),
#                 "created_at": _random_created_at(rng, 120).strftime("%Y-%m-%d %H:%M:%S"),
#             }
#         )

#     all_post_ids = list(range(1, 5 + SAMPLE_COUNT))
#     scrap_pairs = set()
#     attempts = 0
#     while len(scraps) < SAMPLE_COUNT and attempts < SAMPLE_COUNT * 20:
#         attempts += 1
#         user_id = rng.choice(all_user_ids)
#         post_id = rng.choice(all_post_ids)
#         pair = (user_id, post_id)
#         if pair in scrap_pairs:
#             continue
#         scrap_pairs.add(pair)
#         scraps.append(
#             {
#                 "user_id": user_id,
#                 "post_id": post_id,
#                 "created_at": _random_created_at(rng, 90).strftime("%Y-%m-%d %H:%M:%S"),
#             }
#         )

#     for i in range(SAMPLE_COUNT):
#         comments.append(
#             {
#                 "comment_id": 6 + i,
#                 "post_id": rng.choice(all_post_ids),
#                 "user_id": rng.choice(all_user_ids),
#                 "content": COMMENT_SAMPLES[i % len(COMMENT_SAMPLES)],
#                 "parent_id": None,
#                 "created_at": _random_created_at(rng, 60).strftime("%Y-%m-%d %H:%M:%S"),
#             }
#         )

#     return {"users": users, "posts": posts, "scraps": scraps, "comments": comments}


# def write_sql(data):
#     lines = [
#         "-- 모델 학습/전처리용 임의 샘플 데이터 (Users/Posts/Scraps/Comments 각 50건)",
#         "-- schema.sql + seed.sql 적용 후 실행하세요. 기존 데모 데이터(1~4번)는 유지됩니다.",
#         "",
#         "USE our_trip_db;",
#         "",
#     ]

#     user_values = []
#     for user in data["users"]:
#         user_values.append(
#             f"({user['user_id']}, {_sql_str(user['email'])}, {_sql_str(user['password'])}, "
#             f"{_sql_str(user['nickname'])}, {_sql_str(user['gender'])}, {user['birth_year']}, "
#             f"NULL, 'user', {_sql_str(user['created_at'])})"
#         )
#     lines.append(
#         "INSERT IGNORE INTO Users (user_id, email, password, nickname, gender, birth_year, profile_image_url, role, created_at) VALUES"
#     )
#     lines.append(",\n".join(user_values) + ";")
#     lines.append("")

#     post_values = []
#     for post in data["posts"]:
#         post_values.append(
#             f"({post['post_id']}, {post['user_id']}, {_sql_str(post['title'])}, {_sql_str(post['content'])}, "
#             f"{_sql_str(post['location_country'])}, {_sql_str(post['location_city'])}, "
#             f"{_sql_str(post['travel_start_date'])}, {_sql_str(post['travel_end_date'])}, "
#             f"{post['view_count']}, {_sql_str(post['created_at'])})"
#         )
#     lines.append(
#         "INSERT IGNORE INTO Posts (post_id, user_id, title, content, location_country, location_city, "
#         "travel_start_date, travel_end_date, view_count, created_at) VALUES"
#     )
#     lines.append(",\n".join(post_values) + ";")
#     lines.append("")

#     scrap_values = []
#     for scrap in data["scraps"]:
#         scrap_values.append(
#             f"({scrap['user_id']}, {scrap['post_id']}, {_sql_str(scrap['created_at'])})"
#         )
#     lines.append("INSERT IGNORE INTO Scraps (user_id, post_id, created_at) VALUES")
#     lines.append(",\n".join(scrap_values) + ";")
#     lines.append("")

#     comment_values = []
#     for comment in data["comments"]:
#         comment_values.append(
#             f"({comment['comment_id']}, {comment['post_id']}, {comment['user_id']}, "
#             f"{_sql_str(comment['content'])}, NULL, {_sql_str(comment['created_at'])})"
#         )
#     lines.append(
#         "INSERT IGNORE INTO Comments (comment_id, post_id, user_id, content, parent_id, created_at) VALUES"
#     )
#     lines.append(",\n".join(comment_values) + ";")
#     lines.append("")

#     OUT_SQL.write_text("\n".join(lines), encoding="utf-8")


# def write_json(data):
#     summary = {
#         "description": "Our Trip recommendation model sample dataset",
#         "record_count": sum(len(rows) for rows in data.values()),
#         "tables": {name: len(rows) for name, rows in data.items()},
#         "data": data,
#     }
#     OUT_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


# def main():
#     data = build_dataset()
#     write_sql(data)
#     write_json(data)
#     counts = {name: len(rows) for name, rows in data.items()}
#     print(f"Generated per table: {counts} -> {OUT_SQL.name}")


# if __name__ == "__main__":
#     main()
