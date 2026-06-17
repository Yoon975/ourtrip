"""
시드/대량 샘플 게시글(post_{id}_main.jpg)만 국가·도시 키워드로 실사 이미지를 받아 넣습니다.
사용자가 업로드한 이미지(uuid 파일명)와 게시글 작성/수정 업로드 흐름은 건드리지 않습니다.
"""
import argparse
import hashlib
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from io import BytesIO
from pathlib import Path

import pymysql
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.config import Config

USER_AGENT = "OurTripBot/1.0 (our-trip local; educational)"
POST_SIZE = (960, 540)
BULK_IMAGE_PATTERN = re.compile(r"^uploads/posts/post_\d+_", re.IGNORECASE)
CACHE_DIR = Config.UPLOAD_ROOT / "location_cache"

COUNTRY_EN = {
    "대한민국": "South Korea",
    "일본": "Japan",
    "태국": "Thailand",
    "베트남": "Vietnam",
    "프랑스": "France",
    "스페인": "Spain",
    "이탈리아": "Italy",
    "미국": "United States",
    "호주": "Australia",
    "중국": "China",
    "싱가포르": "Singapore",
    "대만": "Taiwan",
    "캐나다": "Canada",
    "영국": "United Kingdom",
    "스위스": "Switzerland",
    "체코": "Czech Republic",
    "인도네시아": "Indonesia",
    "이탈리아": "Italy",
}

CITY_EN = {
    ("대한민국", "서울"): "Seoul",
    ("대한민국", "부산"): "Busan",
    ("대한민국", "제주"): "Jeju",
    ("대한민국", "강릉"): "Gangneung",
    ("대한민국", "전주"): "Jeonju",
    ("대한민국", "여수"): "Yeosu",
    ("일본", "도쿄"): "Tokyo",
    ("일본", "교토"): "Kyoto",
    ("일본", "후쿠오카"): "Fukuoka",
    ("일본", "삿포로"): "Sapporo",
    ("일본", "오사카"): "Osaka",
    ("태국", "방콕"): "Bangkok",
    ("태국", "치앙마이"): "Chiang Mai",
    ("태국", "푸켓"): "Phuket",
    ("베트남", "다낭"): "Da Nang",
    ("베트남", "하노이"): "Hanoi",
    ("베트남", "호치민"): "Ho Chi Minh City",
    ("프랑스", "파리"): "Paris",
    ("프랑스", "니스"): "Nice",
    ("스페인", "바르셀로나"): "Barcelona",
    ("스페인", "마드리드"): "Madrid",
    ("이탈리아", "로마"): "Rome",
    ("이탈리아", "밀라노"): "Milan",
    ("미국", "뉴욕"): "New York",
    ("미국", "로스앤젤레스"): "Los Angeles",
    ("호주", "시드니"): "Sydney",
    ("호주", "멜bourne"): "Melbourne",
    ("중국", "상하이"): "Shanghai",
    ("중국", "베이징"): "Beijing",
    ("싱가포르", "싱가포르"): "Singapore",
    ("대만", "타이pei"): "Taipei",
    ("캐나다", "밴쿠버"): "Vancouver",
    ("영국", "런don"): "London",
    ("스위스", "취리히"): "Zurich",
    ("체코", "프라ha"): "Prague",
    ("인도네시아", "발리"): "Bali",
}


def _absolute_path(relative_path):
    parts = relative_path.replace("\\", "/").split("/")
    return Config.UPLOAD_ROOT.parent.joinpath(*parts)


def _search_queries(country, city):
    city_en = CITY_EN.get((country, city), city)
    country_en = COUNTRY_EN.get(country, country)
    return [
        f"{city_en} {country_en} travel",
        f"{city_en} {country_en} cityscape",
        f"{city_en} landmark",
        f"{country_en} {city_en}",
    ]


def _http_json(url, headers=None):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, **(headers or {})})
    with urllib.request.urlopen(request, timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def _search_openverse(query, page_size=20):
    params = urllib.parse.urlencode(
        {
            "q": query,
            "page_size": page_size,
            "license_type": "commercial,modification",
            "aspect_ratio": "wide",
        }
    )
    url = f"https://api.openverse.org/v1/images/?{params}"
    data = _http_json(url)
    urls = []
    for item in data.get("results", []):
        candidate = item.get("url") or item.get("thumbnail")
        if candidate and candidate.startswith("http"):
            urls.append(candidate)
    return urls


def _search_pexels(query, api_key, per_page=12):
    params = urllib.parse.urlencode({"query": query, "per_page": per_page, "orientation": "landscape"})
    url = f"https://api.pexels.com/v1/search?{params}"
    data = _http_json(url, headers={"Authorization": api_key})
    urls = []
    for photo in data.get("photos", []):
        src = photo.get("src") or {}
        candidate = src.get("large") or src.get("medium") or src.get("original")
        if candidate:
            urls.append(candidate)
    return urls


def _search_wikimedia(query, limit=12):
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrlimit": str(limit),
        "gsrnamespace": "6",
        "prop": "imageinfo",
        "iiprop": "url|mime|thumburl",
        "iiurlwidth": "1200",
        "format": "json",
    }
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode(params)
    data = _http_json(url)
    pages = data.get("query", {}).get("pages", {})
    urls = []
    for page in pages.values():
        for info in page.get("imageinfo", []):
            mime = info.get("mime", "")
            if not mime.startswith("image/"):
                continue
            if mime in ("image/svg+xml", "image/gif"):
                continue
            candidate = info.get("thumburl") or info.get("url")
            if candidate:
                urls.append(candidate)
    return urls


def _download_bytes(url):
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def _save_cover_jpeg(raw_bytes, output_path):
    image = Image.open(BytesIO(raw_bytes))
    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    elif image.mode == "L":
        image = image.convert("RGB")

    src_w, src_h = image.size
    target_w, target_h = POST_SIZE
    scale = max(target_w / src_w, target_h / src_h)
    resized = image.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    cropped = resized.crop((left, top, left + target_w, top + target_h))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    cropped.save(output_path, format="JPEG", quality=88)


def _location_key(country, city):
    return f"{country}|{city}"


def _cache_folder(country, city):
    digest = hashlib.md5(_location_key(country, city).encode("utf-8")).hexdigest()[:12]
    folder = CACHE_DIR / digest
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _is_bad_image_url(url):
    lowered = url.lower()
    blocked = ("map", "chart", "diagram", "logo", "icon", "svg", "coat_of_arms", "flag_of")
    return any(token in lowered for token in blocked)


def _fetch_location_pool(country, city, pool_size, pexels_key, delay):
    folder = _cache_folder(country, city)
    existing = sorted(folder.glob("*.jpg"))
    if len(existing) >= pool_size:
        return existing

    collected_urls = []
    country_en = COUNTRY_EN.get(country, country)
    city_en = CITY_EN.get((country, city), city)
    query_sets = _search_queries(country, city)
    if city_en != country_en:
        query_sets.extend(
            [
                f"{country_en} travel landscape",
                f"{country_en} tourism",
            ]
        )

    for query in query_sets:
        sources = []
        try:
            sources.extend(_search_openverse(query, page_size=15))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            pass
        time.sleep(delay)

        if pexels_key:
            try:
                sources.extend(_search_pexels(query, pexels_key, per_page=8))
            except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
                pass
            time.sleep(delay)

        try:
            sources.extend(_search_wikimedia(query, limit=10))
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
            pass
        time.sleep(delay)

        for url in sources:
            if _is_bad_image_url(url):
                continue
            if url not in collected_urls:
                collected_urls.append(url)
        if len(collected_urls) >= pool_size * 6:
            break

    downloaded = len(existing)
    for url in collected_urls:
        if downloaded >= pool_size:
            break
        target = folder / f"{downloaded + 1:03d}.jpg"
        if target.exists():
            downloaded += 1
            continue
        try:
            raw = _download_bytes(url)
            if len(raw) < 8000:
                continue
            _save_cover_jpeg(raw, target)
            downloaded += 1
            time.sleep(delay)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError, Image.UnidentifiedImageError):
            continue

    return sorted(folder.glob("*.jpg"))


def _pick_cached_image(pool, post_id, image_order):
    if not pool:
        return None
    rng = random.Random(post_id * 1000 + image_order)
    return rng.choice(pool)


def fetch_bulk_post_images(force=False, pool_size=10, limit=None, delay=0.25, refresh_cache=False):
    pexels_key = getattr(Config, "PEXELS_API_KEY", None) or None
    if not pexels_key:
        import os

        pexels_key = os.getenv("PEXELS_API_KEY")

    conn = pymysql.connect(
        host=Config.DB_HOST,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset=Config.DB_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
    )

    updated = 0
    skipped = 0
    pools = {}
    country_pools = {}

    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT pi.post_id, pi.image_url, pi.image_order,
                       p.location_country, p.location_city, p.title
                FROM Post_Images pi
                JOIN Posts p ON p.post_id = pi.post_id
                WHERE pi.image_url REGEXP '^uploads/posts/post_[0-9]+_'
                ORDER BY pi.post_id, pi.image_order
                """
            )
            rows = cursor.fetchall()
            if limit:
                rows = rows[:limit]

            locations = sorted({(row["location_country"], row["location_city"]) for row in rows})
            print(f"대상 게시글 이미지: {len(rows)}건 / 지역 {len(locations)}곳")

            for country, city in locations:
                label = f"{city}, {country}"
                print(f"  수집 중: {label}")
                if refresh_cache:
                    folder = _cache_folder(country, city)
                    for cached in folder.glob("*.jpg"):
                        cached.unlink(missing_ok=True)
                pools[(country, city)] = _fetch_location_pool(
                    country, city, pool_size, pexels_key, delay
                )
                print(f"    -> 캐시 {len(pools[(country, city)])}장")

            countries = sorted({country for country, _ in locations})
            for country in countries:
                needs_fallback = any(len(pools.get(pair, [])) == 0 for pair in locations if pair[0] == country)
                if not needs_fallback:
                    continue
                print(f"  국가 fallback: {country}")
                country_pools[country] = _fetch_location_pool(
                    country,
                    COUNTRY_EN.get(country, country),
                    pool_size,
                    pexels_key,
                    delay,
                )
                print(f"    -> 국가 캐시 {len(country_pools[country])}장")

            for row in rows:
                output = _absolute_path(row["image_url"])
                if output.exists() and not force:
                    skipped += 1
                    continue

                pool = pools.get((row["location_country"], row["location_city"]), [])
                cached = _pick_cached_image(pool, row["post_id"], row.get("image_order") or 1)
                if not cached:
                    country_pool = country_pools.get(row["location_country"], [])
                    cached = _pick_cached_image(country_pool, row["post_id"], row.get("image_order") or 1)
                if not cached:
                    skipped += 1
                    continue

                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_bytes(cached.read_bytes())
                updated += 1

    finally:
        conn.close()

    return {
        "updated": updated,
        "skipped": skipped,
        "locations": len(pools),
    }


def main():
    parser = argparse.ArgumentParser(description="bulk/seed 게시글에 지역별 실사 이미지 적용")
    parser.add_argument("--force", action="store_true", help="기존 bulk 이미지도 덮어쓰기")
    parser.add_argument("--pool-size", type=int, default=10, help="지역당 캐시 이미지 수")
    parser.add_argument("--limit", type=int, default=None, help="테스트용 처리 건수 제한")
    parser.add_argument("--refresh-cache", action="store_true", help="지역 캐시를 비우고 다시 받기")
    parser.add_argument("--delay", type=float, default=0.25, help="API 호출 간격(초)")
    args = parser.parse_args()

    try:
        result = fetch_bulk_post_images(
            force=args.force,
            pool_size=args.pool_size,
            limit=args.limit,
            delay=args.delay,
            refresh_cache=args.refresh_cache,
        )
    except pymysql.err.OperationalError as exc:
        print("DB 연결 실패:", exc)
        sys.exit(1)

    print(
        f"완료: {result['updated']}장 적용, {result['skipped']}장 건너뜀 "
        f"(지역 {result['locations']}곳). uuid 업로드 이미지는 변경하지 않았습니다."
    )


if __name__ == "__main__":
    main()
