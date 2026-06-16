-- 기존 테이블이 존재할 경우 삭제 (순서는 역순으로)
DROP TABLE IF EXISTS Scraps;
DROP TABLE IF EXISTS Comments;
DROP TABLE IF EXISTS Post_Images;
DROP TABLE IF EXISTS Posts;
DROP TABLE IF EXISTS Users;

-- 1. 회원 테이블 (Users)
CREATE TABLE Users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    nickname VARCHAR(50) NOT NULL UNIQUE,
    gender ENUM('M', 'F', 'U') DEFAULT 'U', -- M: 남성, F: 여성, U: 미선택
    birth_year INT,                         -- 나이대 분석용 (출생년도 저장)
    profile_image_url VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. 여행 게시글 테이블 (Posts)
CREATE TABLE Posts (
    post_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    location_country VARCHAR(100) NOT NULL, -- 분석용 국가 정보
    location_city VARCHAR(100),            -- 분석용 도시 정보
    travel_start_date DATE,                 -- 여행 기간 분석용 시작일
    travel_end_date DATE,                   -- 여행 기간 분석용 종료일
    view_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
);

-- 3. 게시글 이미지 테이블 (Post_Images)
CREATE TABLE Post_Images (
    image_id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    image_url VARCHAR(255) NOT NULL,
    image_order INT DEFAULT 1,
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES Posts(post_id) ON DELETE CASCADE
);

-- 4. 댓글 및 대댓글 테이블 (Comments)
CREATE TABLE Comments (
    comment_id INT AUTO_INCREMENT PRIMARY KEY,
    post_id INT NOT NULL,
    user_id INT NOT NULL,
    content TEXT NOT NULL,
    parent_id INT DEFAULT NULL,              -- 대댓글 구현을 위한 셀프 참조 외래키
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (post_id) REFERENCES Posts(post_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (parent_id) REFERENCES Comments(comment_id) ON DELETE CASCADE
);

-- 5. 스크랩 테이블 (Scraps)
CREATE TABLE Scraps (
    scrap_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    post_id INT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY unique_user_post (user_id, post_id), -- 중복 스크랩 방지
    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (post_id) REFERENCES Posts(post_id) ON DELETE CASCADE
);
