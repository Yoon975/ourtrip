"""DB에 등록된 사용자/게시글용 플레이스홀더 이미지를 생성합니다. DB 데이터는 삭제하지 않습니다."""
import pathlib
import random
import sys

import pymysql
from PIL import Image, ImageDraw, ImageFont

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Config

PROFILE_SIZE = (400, 400)
POST_SIZE = (960, 540)

PALETTE = [
    (74, 111, 165),
    (61, 122, 94),
    (196, 120, 84),
    (120, 92, 156),
    (84, 130, 150),
    (170, 110, 90),
    (90, 140, 120),
    (140, 100, 130),
]


def _pick_color(seed_value):
    rng = random.Random(seed_value)
    base = PALETTE[rng.randint(0, len(PALETTE) - 1)]
    return tuple(min(255, c + rng.randint(-15, 25)) for c in base)


def _load_font(size, bold=False):
    candidates = [
        "C:/Windows/Fonts/malgunbd.ttf" if bold else "C:/Windows/Fonts/malgun.ttf",
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
    ]
    for path in candidates:
        if pathlib.Path(path).exists():
            try:
                return ImageFont.truetype(path, size=size)
            except OSError:
                continue
    return ImageFont.load_default()


def _absolute_path(relative_path):
    parts = relative_path.replace("\\", "/").split("/")
    return Config.UPLOAD_ROOT.parent.joinpath(*parts)


def _ensure_parent(path):
    path.parent.mkdir(parents=True, exist_ok=True)


def _draw_profile_image(nickname, user_id, output_path):
    color = _pick_color(user_id)
    accent = tuple(min(255, c + 40) for c in color)
    image = Image.new("RGB", PROFILE_SIZE, color)
    draw = ImageDraw.Draw(image)

    draw.ellipse(
        (40, 40, PROFILE_SIZE[0] - 40, PROFILE_SIZE[1] - 40),
        fill=accent,
        outline=(255, 255, 255),
        width=4,
    )

    label = (nickname or "?")[:1]
    font = _load_font(120, bold=True)
    bbox = draw.textbbox((0, 0), label, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    draw.text(
        ((PROFILE_SIZE[0] - text_w) / 2, (PROFILE_SIZE[1] - text_h) / 2 - 8),
        label,
        fill=(255, 255, 255),
        font=font,
    )

    _ensure_parent(output_path)
    image.save(output_path, format="JPEG", quality=88)


def _draw_post_image(title, country, city, post_id, output_path):
    color = _pick_color(post_id * 17)
    darker = tuple(max(0, c - 35) for c in color)
    image = Image.new("RGB", POST_SIZE, color)
    draw = ImageDraw.Draw(image)

    for y in range(POST_SIZE[1]):
        ratio = y / POST_SIZE[1]
        row_color = tuple(int(color[i] * (1 - ratio * 0.35) + darker[i] * ratio * 0.35) for i in range(3))
        draw.line([(0, y), (POST_SIZE[0], y)], fill=row_color)

    draw.rectangle((36, 36, POST_SIZE[0] - 36, POST_SIZE[1] - 36), outline=(255, 255, 255), width=3)

    title_font = _load_font(42, bold=True)
    meta_font = _load_font(28)
    small_font = _load_font(22)

    location = " · ".join(part for part in [city, country] if part)
    lines = [title[:28], location or "Our Trip", f"POST #{post_id:03d}"]

    y = 120
    for idx, line in enumerate(lines):
        font = title_font if idx == 0 else meta_font if idx == 1 else small_font
        draw.text((72, y), line, fill=(255, 255, 255), font=font)
        y += 64 if idx == 0 else 48

    _ensure_parent(output_path)
    image.save(output_path, format="JPEG", quality=88)


def generate_all():
    Config.UPLOAD_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
    Config.UPLOAD_POST_DIR.mkdir(parents=True, exist_ok=True)

    conn = pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset=Config.DB_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
    )

    profile_count = 0
    post_image_count = 0
    post_insert_count = 0

    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT user_id, nickname, profile_image_url FROM Users ORDER BY user_id")
            users = cursor.fetchall()

            for user in users:
                relative = user["profile_image_url"] or f"uploads/profiles/user_{user['user_id']}.jpg"
                output = _absolute_path(relative)
                if not output.exists():
                    _draw_profile_image(user["nickname"], user["user_id"], output)
                profile_count += 1

                if not user["profile_image_url"]:
                    cursor.execute(
                        "UPDATE Users SET profile_image_url = %s WHERE user_id = %s",
                        (relative.replace("\\", "/"), user["user_id"]),
                    )

            cursor.execute(
                """
                SELECT p.post_id, p.title, p.location_country, p.location_city
                FROM Posts p
                ORDER BY p.post_id
                """
            )
            posts = cursor.fetchall()

            cursor.execute("SELECT post_id, image_url, image_order FROM Post_Images ORDER BY post_id, image_order")
            existing_images = cursor.fetchall()
            images_by_post = {}
            for row in existing_images:
                images_by_post.setdefault(row["post_id"], []).append(row)

            for post in posts:
                post_id = post["post_id"]
                rows = images_by_post.get(post_id, [])

                if not rows:
                    relative = f"uploads/posts/post_{post_id}_main.jpg"
                    cursor.execute(
                        "INSERT INTO Post_Images (post_id, image_url, image_order) VALUES (%s, %s, 1)",
                        (post_id, relative),
                    )
                    post_insert_count += 1
                    rows = [{"image_url": relative}]

                for row in rows:
                    output = _absolute_path(row["image_url"])
                    if not output.exists():
                        _draw_post_image(
                            post["title"],
                            post["location_country"],
                            post["location_city"],
                            post_id,
                            output,
                        )
                    post_image_count += 1

        conn.commit()
    finally:
        conn.close()

    return profile_count, post_image_count, post_insert_count


def main():
    try:
        profiles, post_images, inserted = generate_all()
    except pymysql.err.OperationalError as exc:
        print("DB 연결 실패:", exc)
        sys.exit(1)
    except ImportError:
        print("Pillow가 필요합니다: pip install Pillow")
        sys.exit(1)

    print(
        f"이미지 생성 완료: 프로필 {profiles}장, 게시글 {post_images}장 "
        f"(Post_Images 신규 등록 {inserted}건)"
    )


if __name__ == "__main__":
    main()
