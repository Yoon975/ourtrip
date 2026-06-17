from app.exceptions import ValidationError


def validate_post_payload(data):
    errors = {}
    title = (data.get("title") or "").strip()
    content = (data.get("content") or "").strip()
    country = (data.get("location_country") or "").strip()
    city = (data.get("location_city") or "").strip()

    if not title:
        errors["title"] = "제목을 입력해 주세요."
    elif len(title) > 200:
        errors["title"] = "제목은 200자 이하여야 합니다."

    if not content:
        errors["content"] = "내용을 입력해 주세요."

    if not country:
        errors["location_country"] = "국가를 입력해 주세요."

    if errors:
        raise ValidationError("입력값을 확인해 주세요.", errors=errors)

    return {
        "title": title,
        "content": content,
        "location_country": country,
        "location_city": city or None,
        "travel_start_date": data.get("travel_start_date") or None,
        "travel_end_date": data.get("travel_end_date") or None,
    }
