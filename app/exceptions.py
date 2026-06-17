class AppException(Exception):
    status_code = 400
    message = "요청 처리 중 오류가 발생했습니다."

    def __init__(self, message=None):
        if message:
            self.message = message
        super().__init__(self.message)


class NotFoundError(AppException):
    status_code = 404
    message = "요청한 리소스를 찾을 수 없습니다."


class ValidationError(AppException):
    status_code = 422
    message = "입력값이 올바르지 않습니다."

    def __init__(self, message=None, errors=None):
        self.errors = errors or {}
        super().__init__(message)


class DuplicateError(AppException):
    status_code = 409
    message = "이미 존재하는 데이터입니다."


class UnauthorizedError(AppException):
    status_code = 401
    message = "로그인이 필요합니다."


class ForbiddenError(AppException):
    status_code = 403
    message = "접근 권한이 없습니다."


class StorageError(AppException):
    status_code = 500
    message = "파일 저장 중 오류가 발생했습니다."
