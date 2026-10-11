"""Domain exceptions raised by the service layer; the router maps them to HTTP codes."""


class SessionServiceError(Exception):
    """Base class. `message` is safe to show to API clients."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message: str = message


class SessionNotFoundError(SessionServiceError):
    """No session exists with the requested id (HTTP 404)."""

    def __init__(self, session_id: int) -> None:
        super().__init__(f"Session {session_id} not found.")
        self.session_id: int = session_id


class InvalidTransitionError(SessionServiceError):
    """The requested lifecycle action is not allowed in the current state (HTTP 409)."""


class PersistenceError(SessionServiceError):
    """A database failure or inconsistent stored data (HTTP 500)."""