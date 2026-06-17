"""DB에 등록된 사용자/게시글용 플레이스홀더 이미지를 생성합니다. DB 데이터는 삭제하지 않습니다."""
import argparse
import hashlib
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


def _seed_int(*parts):
    text = "|".join(str(part or "") for part in parts)
    digest = hashlib.md5(text.encode("utf-8")).hexdigest()
    return int(digest[:8], 16)


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


def _wrap_text(text, font, max_width, draw):
    words = list(text)
    if len(words) <= 28:
        return [text[:32]]
    lines = []
    current = ""
    for char in words:
        candidate = current + char
        bbox = draw.textbbox((0, 0), candidate, font=font)
        if bbox[2] - bbox[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = char
    if current:
        lines.append(current)
    return lines[:2]


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


def _draw_post_image(title, country, city, post_id, output_path, image_order=1):
    seed = _seed_int(country, city, post_id, image_order)
    color = _pick_color(seed)
    darker = tuple(max(0, c - 45) for c in color)
    image = Image.new("RGB", POST_SIZE, color)
    draw = ImageDraw.Draw(image)

    for y in range(POST_SIZE[1]):
        ratio = y / POST_SIZE[1]
        row_color = tuple(
            int(color[i] * (1 - ratio * 0.4) + darker[i] * ratio * 0.4) for i in range(3)
        )
        draw.line([(0, y), (POST_SIZE[0], y)], fill=row_color)

    draw.rectangle((32, 32, POST_SIZE[0] - 32, POST_SIZE[1] - 32), outline=(255, 255, 255), width=3)

    city_text = (city or "").strip()
    country_text = (country or "").strip()
    location_main = city_text or country_text or "Our Trip"
    location_sub = country_text if city_text and country_text else ""

    badge_font = _load_font(24, bold=True)
    city_font = _load_font(56, bold=True)
    country_font = _load_font(34)
    title_font = _load_font(30, bold=True)
    small_font = _load_font(20)

    draw.rounded_rectangle((56, 56, 230, 98), radius=18, fill=(255, 255, 255))
    draw.text((72, 62), "OUR TRIP", fill=darker, font=badge_font)

    y = 130
    for line in _wrap_text(location_main, city_font, POST_SIZE[0] - 140, draw):
        draw.text((72, y), line, fill=(255, 255, 255), font=city_font)
        y += 62

    if location_sub:
        draw.text((72, y), location_sub, fill=(240, 240, 240), font=country_font)
        y += 52

    y += 12
    draw.line([(72, y), (POST_SIZE[0] - 72, y)], fill=(255, 255, 255), width=2)
    y += 24

    for line in _wrap_text(title or "여행 기록", title_font, POST_SIZE[0] - 140, draw):
        draw.text((72, y), line, fill=(255, 255, 255), font=title_font)
        y += 38

    footer = f"POST #{post_id:04d}"
    if image_order > 1:
        footer += f"  ·  {image_order}번째 사진"
    draw.text((72, POST_SIZE[1] - 72), footer, fill=(230, 230, 230), font=small_font)

    _ensure_parent(output_path)
    image.save(output_path, format="JPEG", quality=88)


def generate_all(force=False, profiles=True, posts=True):
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
    profile_created = 0
    post_image_count = 0
    post_created = 0
    post_insert_count = 0

    try:
        with conn.cursor() as cursor:
            if profiles:
                cursor.execute("SELECT user_id, nickname, profile_image_url FROM Users ORDER BY user_id")
                users = cursor.fetchall()

                for user in users:
                    relative = user["profile_image_url"] or f"uploads/profiles/user_{user['user_id']}.jpg"
                    output = _absolute_path(relative)
                    if force or not output.exists():
                        _draw_profile_image(user["nickname"], user["user_id"], output)
                        profile_created += 1
                    profile_count += 1

                    if not user["profile_image_url"]:
                        cursor.execute(
                            "UPDATE Users SET profile_image_url = %s WHERE user_id = %s",
                            (relative.replace("\\", "/"), user["user_id"]),
                        )

            if posts:
                cursor.execute(
                    """
                    SELECT p.post_id, p.title, p.location_country, p.location_city
                    FROM Posts p
                    ORDER BY p.post_id
                    """
                )
                posts_rows = cursor.fetchall()

                cursor.execute(
                    "SELECT post_id, image_url, image_order FROM Post_Images ORDER BY post_id, image_order"
                )
                existing_images = cursor.fetchall()
                images_by_post = {}
                for row in existing_images:
                    images_by_post.setdefault(row["post_id"], []).append(row)

                for post in posts_rows:
                    post_id = post["post_id"]
                    rows = images_by_post.get(post_id, [])

                    if not rows:
                        relative = f"uploads/posts/post_{post_id}_main.jpg"
                        cursor.execute(
                            "INSERT INTO Post_Images (post_id, image_url, image_order) VALUES (%s, %s, 1)",
                            (post_id, relative),
                        )
                        post_insert_count += 1
                        rows = [{"image_url": relative, "image_order": 1}]

                    for row in rows:
                        output = _absolute_path(row["image_url"])
                        image_order = row.get("image_order") or 1
                        if force or not output.exists():
                            _draw_post_image(
                                post["title"],
                                post["location_country"],
                                post["location_city"],
                                post_id,
                                output,
                                image_order=image_order,
                            )
                            post_created += 1
                        post_image_count += 1

        conn.commit()
    finally:
        conn.close()

    return {
        "profiles": profile_count,
        "profiles_created": profile_created,
        "post_images": post_image_count,
        "post_created": post_created,
        "post_insert_count": post_insert_count,
    }


def main():
    parser = argparse.ArgumentParser(description="Our Trip 플레이스홀더 이미지 생성")
    parser.add_argument(
        "--force",
        action="store_true",
        help="기존 파일이 있어도 국가·도시 라벨로 다시 생성",
    )
    parser.add_argument(
        "--posts-only",
        action="store_true",
        help="게시글 이미지만 생성",
    )
    args = parser.parse_args()

    try:
        result = generate_all(
            force=args.force,
            profiles=not args.posts_only,
            posts=True,
        )
    except pymysql.err.OperationalError as exc:
        print("DB 연결 실패:", exc)
        sys.exit(1)
    except ImportError:
        print("Pillow가 필요합니다: pip install Pillow")
        sys.exit(1)

    mode = "강제 재생성" if args.force else "누락분만 생성"
    print(f"완료 ({mode})")
    if not args.posts_only:
        print(
            f"  프로필: {result['profiles_created']}/{result['profiles']}장 생성"
        )
    print(
        f"  게시글: {result['post_created']}/{result['post_images']}장 생성 "
        f"(Post_Images 신규 {result['post_insert_count']}건)"
    )


if __name__ == "__main__":
    main()
