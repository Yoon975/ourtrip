import uuid
from pathlib import Path

from werkzeug.utils import secure_filename

from app.config import BASE_DIR, Config
from app.exceptions import StorageError, ValidationError


class ImageService:
    PROFILE_SUBDIR = "profiles"
    POST_SUBDIR = "posts"

    def __init__(self):
        Config.UPLOAD_ROOT.mkdir(parents=True, exist_ok=True)
        Config.UPLOAD_PROFILE_DIR.mkdir(parents=True, exist_ok=True)
        Config.UPLOAD_POST_DIR.mkdir(parents=True, exist_ok=True)

    def _validate_file(self, file_storage):
        if not file_storage or not file_storage.filename:
            raise ValidationError("업로드할 이미지를 선택해 주세요.", errors={"file": "필수"})

        extension = file_storage.filename.rsplit(".", 1)[-1].lower()
        if extension not in Config.ALLOWED_IMAGE_EXTENSIONS:
            raise ValidationError(
                "허용되지 않는 이미지 형식입니다.",
                errors={"file": "형식 오류"},
            )

        file_storage.seek(0, 2)
        size = file_storage.tell()
        file_storage.seek(0)
        if size > Config.MAX_IMAGE_SIZE:
            raise ValidationError(
                "이미지 크기는 5MB 이하여야 합니다.",
                errors={"file": "크기 초과"},
            )
        return extension

    def _save(self, file_storage, subdir):
        extension = self._validate_file(file_storage)
        filename = f"{uuid.uuid4().hex}.{extension}"
        target_dir = Config.UPLOAD_ROOT / subdir
        target_dir.mkdir(parents=True, exist_ok=True)
        safe_name = secure_filename(filename)
        absolute_path = target_dir / safe_name

        try:
            file_storage.save(absolute_path)
        except OSError as exc:
            raise StorageError("이미지 저장에 실패했습니다.") from exc

        return f"uploads/{subdir}/{safe_name}".replace("\\", "/")

    def save_profile_image(self, file_storage):
        return self._save(file_storage, self.PROFILE_SUBDIR)

    def save_post_image(self, file_storage):
        return self._save(file_storage, self.POST_SUBDIR)

    def delete_relative(self, relative_path):
        if not relative_path or relative_path.startswith("http"):
            return
        absolute_path = BASE_DIR / "app" / "static" / Path(relative_path)
        if absolute_path.exists() and absolute_path.is_file():
            absolute_path.unlink()
