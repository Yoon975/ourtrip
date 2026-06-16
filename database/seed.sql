-- Our Trip 초기 데이터 (유저 3명 + 게시글/이미지/댓글/스크랩)
-- 비밀번호: 1234 (werkzeug scrypt 해시)
-- schema.sql 실행 후 이 파일을 실행하세요.

USE our_trip_db;

SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE Scraps;
TRUNCATE TABLE Comments;
TRUNCATE TABLE Post_Images;
TRUNCATE TABLE Posts;
TRUNCATE TABLE Users;
SET FOREIGN_KEY_CHECKS = 1;

INSERT INTO Users (user_id, email, password, nickname, gender, birth_year, profile_image_url, role, created_at) VALUES
(1, 'jiyun@ourtrip.com', 'scrypt:32768:8:1$gG2yoMMNqaeKYX0M$ed4ca646273ebeb8c9c83024fd8d1e42c80b208c41f8931fd1c23dcde78ff43d2e09b21e3d2ca04cfb9b4f5dde90d6cb92ba3e7e8a29b445737cfc00cf8a2ab6', '지윤', 'F', 1998, 'uploads/profiles/user_1.jpg', 'user', '2026-01-10 09:00:00'),
(2, 'minho@ourtrip.com', 'scrypt:32768:8:1$gG2yoMMNqaeKYX0M$ed4ca646273ebeb8c9c83024fd8d1e42c80b208c41f8931fd1c23dcde78ff43d2e09b21e3d2ca04cfb9b4f5dde90d6cb92ba3e7e8a29b445737cfc00cf8a2ab6', '민호', 'M', 1995, 'uploads/profiles/user_2.jpg', 'user', '2026-01-12 14:30:00'),
(3, 'sora@ourtrip.com', 'scrypt:32768:8:1$gG2yoMMNqaeKYX0M$ed4ca646273ebeb8c9c83024fd8d1e42c80b208c41f8931fd1c23dcde78ff43d2e09b21e3d2ca04cfb9b4f5dde90d6cb92ba3e7e8a29b445737cfc00cf8a2ab6', '수아', 'F', 2001, 'uploads/profiles/user_3.jpg', 'user', '2026-01-15 11:00:00'),
(4, 'admin@ourtrip.com', 'scrypt:32768:8:1$gG2yoMMNqaeKYX0M$ed4ca646273ebeb8c9c83024fd8d1e42c80b208c41f8931fd1c23dcde78ff43d2e09b21e3d2ca04cfb9b4f5dde90d6cb92ba3e7e8a29b445737cfc00cf8a2ab6', '관리자', 'M', 1990, NULL, 'admin', '2026-01-01 00:00:00');

INSERT INTO Posts (post_id, user_id, title, content, location_country, location_city, travel_start_date, travel_end_date, view_count, created_at) VALUES
(1, 1, '제주도 3박 4일', '한라산 등반과 협재·금능 해변을 돌아본 제주 여행기입니다. 현지 카페와 흑돼지 맛집, 렌트카 동선도 함께 정리했습니다.', '대한민국', '제주', '2026-03-10', '2026-03-13', 128, '2026-03-14 10:00:00'),
(2, 2, '오사카 맛집 투어', '도톤보리와 신세카이를 중심으로 타코야키, 오코노미야키, 라멘을 즐긴 2박 3일 기록입니다. 교통 패스 활용법도 포함했습니다.', '일본', '오사카', '2026-02-05', '2026-02-07', 256, '2026-02-08 18:20:00'),
(3, 3, '강원도 캠핑', '평창 계곡 옆 캠핑장에서 보낸 1박 2일. 장비 체크리스트, 불멍 팁, 별 관측 포인트를 공유합니다.', '대한민국', '평창', '2025-11-20', '2025-11-21', 89, '2025-11-22 09:15:00'),
(4, 1, '부산 바다 산책', '해운대와 광안리를 잇는 바닷길 산책 코스. 저녁에는 광안대교 야경과 횟집 추천 목록을 정리했습니다.', '대한민국', '부산', '2025-12-01', '2025-12-02', 74, '2025-12-03 16:40:00');

INSERT INTO Post_Images (post_id, image_url, image_order) VALUES
(1, 'uploads/posts/post_1_main.jpg', 1),
(1, 'uploads/posts/post_1_sub.jpg', 2),
(2, 'uploads/posts/post_2_main.jpg', 1),
(3, 'uploads/posts/post_3_main.jpg', 1),
(4, 'uploads/posts/post_4_main.jpg', 1);

INSERT INTO Comments (comment_id, post_id, user_id, content, parent_id, created_at) VALUES
(1, 1, 2, '제주 동선 참고해서 계획 세웠어요. 감사합니다!', NULL, '2026-03-15 11:00:00'),
(2, 1, 3, '협재 해변 사진 너무 예뻐요.', NULL, '2026-03-16 09:30:00'),
(3, 1, 1, '도움이 되었다니 다행이에요 :)', 1, '2026-03-15 14:20:00'),
(4, 2, 1, '오사카 라멘집 목록 저장했습니다!', NULL, '2026-02-09 10:00:00'),
(5, 3, 2, '캠핑 장비 리스트 유용해요.', NULL, '2025-11-23 20:10:00');

INSERT INTO Scraps (user_id, post_id, created_at) VALUES
(2, 1, '2026-03-15 12:00:00'),
(2, 4, '2025-12-04 09:00:00'),
(3, 1, '2026-03-16 10:00:00'),
(3, 2, '2026-02-10 11:30:00'),
(1, 3, '2025-11-24 08:00:00');
