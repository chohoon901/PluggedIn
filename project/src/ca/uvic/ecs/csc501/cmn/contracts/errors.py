"""Application errors independent of an HTTP framework."""


class AppError(ValueError):
    def __init__(self, message: str, code: str = 'INVALID_INPUT', status_code: int = 400,
                 field_errors: dict | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.field_errors = field_errors or {}


class InputError(AppError):
    def __init__(self, message: str, field_errors: dict | None = None):
        super().__init__(message, field_errors=field_errors)


class NotFoundError(AppError):
    def __init__(self, message: str):
        super().__init__(message, 'NOT_FOUND', 404)


class ConflictError(AppError):
    def __init__(self, message: str):
        super().__init__(message, 'CONFLICT', 409)


class NotReadyError(AppError):
    def __init__(self, message: str):
        super().__init__(message, 'NOT_READY', 503)
