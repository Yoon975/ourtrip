from app.exceptions import NotFoundError, ValidationError
from app.repositories.message_repository import MessageRepository
from app.repositories.user_repository import UserRepository
from app.services.notification_service import NotificationService
from app.utils.media import media_url


class MessageService:
    def __init__(self, db):
        self.db = db
        self.repo = MessageRepository(db)
        self.user_repo = UserRepository(db)
        self.notification_service = NotificationService(db)

    def list_conversations(self, user_id):
        rows = self.repo.list_conversations(user_id)
        seen = {}
        for row in rows:
            other_id = row["other_user_id"]
            if other_id in seen:
                continue
            unread = 0
            if row["receiver_id"] == user_id and not row["is_read"]:
                unread = 1
            entry = seen.get(other_id)
            if entry:
                entry["unread_count"] += unread
                continue
            seen[other_id] = {
                "other_user_id": other_id,
                "other_nickname": row["other_nickname"],
                "other_profile_image_url": media_url(row.get("other_profile_image_url")),
                "last_message": row["content"],
                "last_message_at": row["created_at"],
                "unread_count": unread,
            }
        return sorted(seen.values(), key=lambda item: item["last_message_at"], reverse=True)

    def get_conversation(self, user_id, other_user_id):
        other = self.user_repo.find_by_id(other_user_id)
        if not other:
            raise NotFoundError("사용자를 찾을 수 없습니다.")
        self.repo.mark_read_from_sender(user_id, other_user_id)
        messages = self.repo.find_conversation(user_id, other_user_id)
        return {
            "other_user": {
                "user_id": other["user_id"],
                "nickname": other["nickname"],
                "profile_image_url": media_url(other.get("profile_image_url")),
            },
            "messages": messages,
        }

    def send_message(self, sender_id, receiver_id, content):
        content = (content or "").strip()
        if not content:
            raise ValidationError("메시지 내용을 입력해 주세요.", errors={"content": "필수"})
        if len(content) > 1000:
            raise ValidationError("메시지는 1000자 이하여야 합니다.", errors={"content": "길이 초과"})
        receiver = self.user_repo.find_by_id(receiver_id)
        if not receiver:
            raise NotFoundError("받는 사람을 찾을 수 없습니다.")
        if sender_id == receiver_id:
            raise ValidationError("본인에게는 메시지를 보낼 수 없습니다.")

        sender = self.user_repo.find_by_id(sender_id)
        message_id = self.repo.create(sender_id, receiver_id, content)
        self.notification_service.notify_message(
            receiver_id,
            sender_id,
            sender["nickname"],
            message_id,
        )
        return self.repo.find_conversation(sender_id, receiver_id)[-1]

    def unread_count(self, user_id):
        return self.repo.count_unread(user_id)
