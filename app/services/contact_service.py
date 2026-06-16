from app.exceptions import ValidationError
from app.repositories.contact_repository import ContactRepository
from app.validators.auth_validator import validate_email


class ContactService:
    def __init__(self, db):
        self.repo = ContactRepository(db)

    def submit_contact(self, name, email, message, user_id=None):
        name = (name or "").strip()
        email = (email or "").strip()
        message = (message or "").strip()
        errors = {}
        if not name:
            errors["name"] = "이름을 입력해 주세요."
        email_error = validate_email(email)
        if email_error:
            errors["email"] = email_error
        if not message:
            errors["message"] = "문의 내용을 입력해 주세요."
        if len(message) > 2000:
            errors["message"] = "문의 내용은 2000자 이하여야 합니다."
        if errors:
            raise ValidationError("입력값을 확인해 주세요.", errors=errors)

        contact_id = self.repo.create(name, email, message, user_id)
        return {"contact_id": contact_id}

    def list_contacts(self, page=1, search=None):
        per_page = 20
        items = self.repo.find_paginated_for_admin(page, per_page, search)
        total = self.repo.count_for_admin(search)
        total_pages = max((total + per_page - 1) // per_page, 1)
        return {
            "items": items,
            "page": page,
            "per_page": per_page,
            "total": total,
            "total_pages": total_pages,
        }

    def delete_contact(self, contact_id):
        self.repo.delete_by_id(contact_id)
        return {"contact_id": contact_id}
