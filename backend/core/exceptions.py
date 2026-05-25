"""Unified exception hierarchy for the backend service layer."""


class AppError(Exception):
    """Base for all application errors."""
    http_status: int = 400

    def __init__(self, message: str, code: str = "error"):
        super().__init__(message)
        self.message = message
        self.code = code


class NotFoundError(AppError):
    http_status = 404

    def __init__(self, resource: str, identifier=None):
        msg = f"{resource} not found" if identifier is None else f"{resource} '{identifier}' not found"
        super().__init__(msg, "not_found")


class AuthError(AppError):
    http_status = 401

    def __init__(self, message: str = "Not authenticated"):
        super().__init__(message, "auth_error")


class PermissionError(AppError):
    http_status = 403

    def __init__(self, action: str = "", resource: str = ""):
        msg = "Permission denied"
        if action and resource:
            msg = f"Permission denied: cannot {action} {resource}"
        elif action:
            msg = f"Permission denied: {action}"
        super().__init__(msg, "permission_denied")


class ValidationError(AppError):
    http_status = 422

    def __init__(self, message: str, field: str = ""):
        super().__init__(message, "validation_error")
        self.field = field


class ConflictError(AppError):
    http_status = 409

    def __init__(self, message: str):
        super().__init__(message, "conflict")


class BusinessRuleError(AppError):
    """Raised when a business rule prevents the operation (not a permission issue)."""
    http_status = 422

    def __init__(self, message: str, rule: str = ""):
        super().__init__(message, "business_rule_violation")
        self.rule = rule


class StateError(BusinessRuleError):
    """Raised when an operation is invalid for the current state of the entity."""

    def __init__(self, current_state: str, attempted_action: str):
        super().__init__(
            f"Cannot '{attempted_action}' when status is '{current_state}'",
            rule="invalid_state_transition",
        )
