"""
auth/session.py — Current user session and permission checks.
Import `session` anywhere to check who is logged in and what they can do.
"""

from database.db import ROLES


class _Session:
    def __init__(self):
        self._user = None
        self._db_perms: set[str] = set()   # cached DB permissions

    # ── Login / logout ────────────────────────────────────────────
    def login(self, user_dict: dict):
        self._user = user_dict
        self._db_perms = set()
        # Sync and cache DB permissions in background-safe way
        try:
            from database.db import sync_user_role, get_user_permissions
            sync_user_role(user_dict["id"], user_dict["role"])
            self._db_perms = get_user_permissions(user_dict["id"])
        except Exception:
            pass

    def logout(self):
        self._user = None
        self._db_perms = set()

    # ── Current user accessors ────────────────────────────────────
    @property
    def user(self):
        return self._user

    @property
    def is_logged_in(self):
        return self._user is not None

    @property
    def user_id(self):
        return self._user["id"] if self._user else None

    @property
    def username(self):
        return self._user["username"] if self._user else "—"

    @property
    def full_name(self):
        return self._user["full_name"] if self._user else "—"

    @property
    def role(self):
        return self._user["role"] if self._user else None

    @property
    def role_label(self):
        if not self.role:
            return "—"
        return ROLES.get(self.role, {}).get("label", self.role.replace("_", " ").title())

    @property
    def role_color(self):
        return ROLES.get(self.role, {}).get("color", "#6B7280")

    @property
    def must_change_password(self):
        return bool(self._user and self._user.get("must_change_pw"))

    # ── Permission checks ─────────────────────────────────────────
    def can(self, permission: str) -> bool:
        """
        Check if the current user has a given permission.
        Checks ROLES dict first (fast), then DB-cached permissions.
        Supports wildcard '*' (admin) and 'module.*' patterns.
        """
        if not self._user:
            return False

        # 1. ROLES dict check (covers built-in role permissions)
        perms = ROLES.get(self.role, {}).get("permissions", [])
        if "*" in perms:
            return True
        if permission in perms:
            return True
        module = permission.split(".")[0]
        if f"{module}.*" in perms:
            return True

        # 2. DB-cached permissions (covers per-user grants and DB-defined roles)
        if "*" in self._db_perms:
            return True
        if permission in self._db_perms:
            return True
        if f"{module}.*" in self._db_perms:
            return True

        return False

    def require(self, permission: str):
        """Raise PermissionError if user doesn't have the permission."""
        if not self.can(permission):
            raise PermissionError(
                f"Your role ({self.role_label}) does not have permission: {permission}"
            )

    # ── Convenience role checks ───────────────────────────────────
    @property
    def is_admin(self):       return self.role == "admin"
    @property
    def is_head_teacher(self): return self.role == "head_teacher"
    @property
    def is_academic(self):    return self.role == "academic"


# Singleton — import this everywhere
session = _Session()
