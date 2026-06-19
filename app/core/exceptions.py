class AppError(Exception):
    """Base application error with API-safe code and message."""

    def __init__(self, code: str, message: str, status_code: int = 400):
        self.code = code
        self.message = message
        self.status_code = status_code
        super().__init__(message)


class EventError(AppError):
    pass
