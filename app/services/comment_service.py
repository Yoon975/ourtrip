from app.exceptions import NotFoundError, ValidationError
from app.repositories.comment_repository import CommentRepository
from app.repositories.post_repository import PostRepository
from app.validators.auth_validator import validate_comment_content


class CommentService:
    def __init__(self, db):
        self.comment_repo = CommentRepository(db)
        self.post_repo = PostRepository(db)

    def get_hierarchical_comments(self, post_id):
        rows = self.comment_repo.find_by_post_id(post_id)
        return self._build_tree(rows)

    def add_comment(self, post_id, user_id, content, parent_id=None):
        content = validate_comment_content(content)
        post = self.post_repo.find_by_id_with_author(post_id)
        if not post:
            raise NotFoundError("게시글을 찾을 수 없습니다.")

        if parent_id is not None:
            parent = self.comment_repo.find_by_id(parent_id)
            if not parent or parent["post_id"] != post_id:
                raise ValidationError("유효하지 않은 부모 댓글입니다.", errors={"parent_id": "invalid"})

        comment_id = self.comment_repo.create(post_id, user_id, content, parent_id)
        return self.comment_repo.get_with_author(comment_id)

    def _build_tree(self, rows):
        nodes = {}
        roots = []

        for row in rows:
            row = dict(row)
            row["replies"] = []
            nodes[row["comment_id"]] = row

        for row in nodes.values():
            parent_id = row.get("parent_id")
            if parent_id and parent_id in nodes:
                nodes[parent_id]["replies"].append(row)
            else:
                roots.append(row)

        return roots
