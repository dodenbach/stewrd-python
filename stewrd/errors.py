"""Stewrd API error."""


class StewrdError(Exception):
    """Raised when the Stewrd API returns a non-2xx response.

    Attributes:
        status:  HTTP status code (e.g. 401).
        code:    Machine-readable error code (e.g. ``"invalid_api_key"``).
        message: Human-readable description.
        docs:    Optional link to relevant documentation.
    """

    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        docs: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.code = code
        self.message = message
        self.docs = docs

    def __repr__(self) -> str:
        return f"StewrdError(status={self.status}, code={self.code!r}, message={self.message!r})"
