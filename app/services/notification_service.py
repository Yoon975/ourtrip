from flask import url_for


class NotificationService:
    TYPE_LABELS = {
        "comment": "새 댓글",
        "reply": "새 답글",
        "scrap": "스크랩",
        "message": "새 메시지",
    }

    def __init__(self, db):
        from app.repositories.notification_repository import NotificationRepository

        self.repo = NotificationRepository(db)

    def notify_comment(self, post, comment, actor_id, actor_nickname):
        if post["user_id"] == actor_id:
            return
        link = url_for("main.post_detail", post_id=post["post_id"])
        self.repo.create(
            user_id=post["user_id"],
            type_="comment",
            actor_id=actor_id,
            post_id=post["post_id"],
            comment_id=comment["comment_id"],
            content=f"{actor_nickname}님이 '{post['title']}'에 댓글을 남겼습니다.",
            link_url=link,
        )

    def notify_reply(self, post, parent_comment, comment, actor_id, actor_nickname):
        if parent_comment["user_id"] == actor_id:
            return
        link = url_for("main.post_detail", post_id=post["post_id"])
        self.repo.create(
            user_id=parent_comment["user_id"],
            type_="reply",
            actor_id=actor_id,
            post_id=post["post_id"],
            comment_id=comment["comment_id"],
            content=f"{actor_nickname}님이 회원님의 댓글에 답글을 남겼습니다.",
            link_url=link,
        )

    def notify_scrap(self, post, actor_id, actor_nickname):
        if post["user_id"] == actor_id:
            return
        link = url_for("main.post_detail", post_id=post["post_id"])
        self.repo.create(
            user_id=post["user_id"],
            type_="scrap",
            actor_id=actor_id,
            post_id=post["post_id"],
            content=f"{actor_nickname}님이 '{post['title']}'을(를) 스크랩했습니다.",
            link_url=link,
        )

    def notify_message(self, receiver_id, sender_id, sender_nickname, message_id):
        link = url_for("message.conversation", user_id=sender_id)
        self.repo.create(
            user_id=receiver_id,
            type_="message",
            actor_id=sender_id,
            message_id=message_id,
            content=f"{sender_nickname}님이 메시지를 보냈습니다.",
            link_url=link,
        )

    def get_summary(self, user_id):
        return {
            "unread_count": self.repo.count_unread(user_id),
            "items": self.repo.find_recent(user_id, limit=10),
        }

    def list_notifications(self, user_id):
        return self.repo.find_recent(user_id, limit=30)

    def mark_read(self, user_id, notification_id):
        self.repo.mark_read(user_id, notification_id)

    def mark_all_read(self, user_id):
        self.repo.mark_all_read(user_id)
