# Our Trip

여행 기록을 공유하고, ML 기반 **For You** 추천을 제공하는 Flask 커뮤니티 웹 애플리케이션입니다.

---

## 주요 기능

| 영역 | 기능 |
|---|---|
| **커뮤니티** | 게시글 작성·수정·삭제, 다중 이미지, 댓글/대댓글, 스크랩 |
| **소셜** | DM, 알림, 프로필·Travel Log |
| **검색** | 홈에서 제목·국가·도시 필터 |
| **추천** | Random Forest 여행지 예측 + 3단계 하이브리드 랭킹 (For You) |
| **계정** | 비밀번호 변경·찾기, 이메일 변경, 회원 탈퇴 |
| **관리자** | 회원/게시글/댓글/스크랩/문의 관리, 추천 모델 학습 |

---

## 기술 스택

- **Backend:** Python 3.10+, Flask
- **Database:** MySQL (PyMySQL)
- **ML:** scikit-learn, pandas, joblib (Random Forest, TF-IDF, LTR)
- **Frontend:** Jinja2 SSR, Vanilla JS, CSS
- **보안:** scrypt 비밀번호, CSRF 토큰, HttpOnly·SameSite 세션 쿠키

---

## 프로젝트 구조

```
our_trip/
├── app/
│   ├── controllers/      # HTTP 라우트 (Blueprint)
│   ├── services/         # 비즈니스 로직
│   ├── repositories/     # DB 접근
│   ├── preprocessing/    # 추천 ML 전처리·랭킹
│   ├── templates/        # Jinja2 HTML
│   ├── static/           # CSS, JS, uploads
│   └── config.py
├── database/
│   ├── schema.sql        # 전체 스키마 (신규 DB용)
│   ├── seed.sql          # 초기 샘플 데이터
│   └── migrations/       # 증분 마이그레이션
├── scripts/              # 유틸·평가·이미지·마이그레이션 스크립트
├── run.py                # 앱 실행 진입점
├── seed_db.py            # ⚠ DB 전체 초기화 (주의)
└── seed_bulk_data.py     # 대량 샘플 추가 (기존 DB 유지)
```

---

## 시작하기

### 1. 요구 사항

- Python 3.10+
- MySQL 8.x (또는 5.7+)

### 2. 저장소 클론 및 의존성 설치

```bash
git clone <repository-url>
cd our_trip
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. 환경 변수

`.env.example`을 복사해 `.env`를 만듭니다.

```bash
copy .env.example .env   # Windows
# cp .env.example .env   # macOS / Linux
```

```env
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=our_trip_db
SECRET_KEY=generate-a-long-random-secret-key
```

### 4. 데이터베이스 설정

**방법 A — 신규 설치 (스키마 + 초기 데이터)**

```bash
# MySQL에서 DB 생성
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS our_trip_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

python seed_db.py
python scripts/run_migration.py
```

> **주의:** `seed_db.py`는 모든 테이블을 **DROP/TRUNCATE** 합니다. 기존 데이터가 삭제됩니다.

**방법 B — 기존 DB에 기능만 추가**

```bash
python scripts/run_migration.py
```

**방법 C — 대량 샘플 데이터 (선택, ~1,400게시글)**

```bash
python seed_bulk_data.py
```

### 5. 앱 실행

```bash
python run.py
```

브라우저에서 [http://127.0.0.1:5000](http://127.0.0.1:5000) 접속

---

## 테스트 계정 (`seed.sql` 기준)

| 역할 | 이메일 | 비밀번호 |
|---|---|---|
| 일반 사용자 | `jiyun@ourtrip.com` | `1234` |
| 관리자 | `admin@ourtrip.com` | `1234` |

---

## 추천 모델

1. 관리자로 로그인 → [/admin](http://127.0.0.1:5000/admin)
2. **모델 생성** 또는 **모델 재학습** 클릭
3. 학습된 모델은 `app/models/destination_rf.joblib`에 저장 (gitignore)

### 추천 파이프라인 (v4)

```
사용자 피처 (나이·성별·스크랩/작성·여행)
    → Random Forest (여행지 Top-3)
    → 3단계 랭킹 (TF-IDF + 의미 벡터 + 협업 + PostViews + LTR)
    → For You 3건 + 추천 이유
```

### 지표 확인

```bash
python scripts/evaluate_current_model.py
```

---

## 유틸 스크립트

| 스크립트 | 용도 |
|---|---|
| `scripts/run_migration.py` | `database/migrations/*.sql` 적용 |
| `scripts/evaluate_current_model.py` | 추천 모델·랭킹 지표 출력 |
| `scripts/generate_placeholder_images.py` | 플레이스홀더 이미지 생성 (`--force`) |
| `scripts/fetch_location_post_images.py` | bulk 게시글에 지역별 실사 이미지 적용 |
| `scripts/seed_training_postviews.py` | PostViews 시뮬레이션 + 재학습 (개발용) |

---

## 주요 URL

| 경로 | 설명 |
|---|---|
| `/` | 홈 (게시글 목록, For You, 검색) |
| `/write` | 글 작성 |
| `/login`, `/register` | 로그인·회원가입 |
| `/forgot-password` | 비밀번호 찾기 |
| `/profile/account` | 계정 설정 (비밀번호·이메일·탈퇴) |
| `/messages` | DM |
| `/scraps` | 내 스크랩 |
| `/admin` | 관리자 대시보드 |

---

## 보안

- 모든 변경 요청(POST/PUT/PATCH/DELETE)에 **CSRF 토큰** 검증
- HTML 폼: `csrf_token` hidden 필드
- fetch API: `X-CSRF-Token` 헤더 (`static/js/csrf.js`가 자동 주입)
- 세션 쿠키: `HttpOnly`, `SameSite=Lax`
- HTTPS 배포 시 `.env`에 `SESSION_COOKIE_SECURE=true` 설정

비밀번호 찾기는 개발 환경에서 재설정 링크를 화면에 표시합니다. 운영 환경에서는 `PASSWORD_RESET_DEV_LINK=false`로 설정하고 SMTP 연동을 권장합니다.

---

## 개발 시 주의

| 명령 | 설명 |
|---|---|
| `python run.py` | 일반 실행 — **매번 `seed_db.py` 실행하지 않음** |
| `python seed_db.py` | DB **전체 초기화** — 필요할 때만 |
| `python seed_bulk_data.py` | 기존 DB 유지, 샘플만 추가 |

생성 파일 (gitignore):

- `app/models/*.joblib` — 학습된 추천 모델
- `database/recommendation_training.csv` — ML 학습 CSV
- `app/static/uploads/**` — 업로드·캐시 이미지

---

## 라이선스

교육·포트폴리오 목적 프로젝트입니다. bulk 이미지(`fetch_location_post_images.py`)는 Openverse/Wikimedia 등 외부 소스를 사용하므로 배포 시 각 이미지 라이선스를 확인하세요.
