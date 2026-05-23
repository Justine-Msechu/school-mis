"""
services/auth_service.py — Authentication and user management logic.

Access control enforcement flow for every user action:
  1. authenticate()    — verify credentials
  2. session.can()     — RBAC permission check (role-based)
  3. policy_engine.enforce() — policy rule evaluation
  4. get_class_scope() — scope check (class/department)
  5. Action executes   — or PolicyViolation/ServiceError raised
"""

from __future__ import annotations
from services.base import BaseService, ServiceError
from database.db import (
    fetch_one, fetch_all, execute,
    authenticate, create_user, hash_password, verify_password,
)


class AuthService(BaseService):

    # ── Authentication ────────────────────────────────────────────────────────

    def login(self, username: str, password: str) -> dict:
        """
        Authenticate user and populate session.
        Loads DB permissions into session._db_perms.
        Returns user dict on success, raises ServiceError on failure.
        """
        user = authenticate(username.strip(), password)
        if not user:
            raise ServiceError("Invalid username or password.")
        if not user.get("is_active"):
            raise ServiceError("This account has been deactivated.")
        self._session.login(user)
        return user

    def logout(self) -> None:
        self._session.logout()

    def change_password(
        self, user_id: int, current_password: str, new_password: str
    ) -> None:
        """
        Change a user's password. Users can only change their own password
        unless they are an admin.
        """
        if user_id != self._session.user_id and not self._session.is_admin:
            raise ServiceError("You can only change your own password.")

        if not new_password or len(new_password) < 6:
            raise ServiceError("New password must be at least 6 characters.")

        user = fetch_one("SELECT * FROM users WHERE id=?", (user_id,))
        if not user:
            raise ServiceError("User not found.")

        # Verify current password (admins resetting others skip this check)
        if user_id == self._session.user_id:
            if not verify_password(current_password, user["password_hash"], user["salt"]):
                raise ServiceError("Current password is incorrect.")

        h, salt = hash_password(new_password)
        execute(
            "UPDATE users SET password_hash=?, salt=?, must_change_pw=0 WHERE id=?",
            (h, salt, user_id),
        )
        self._audit("password_changed", "users", user_id,
                    detail=f"Password changed for user {user['username']}")

    # ── User management ───────────────────────────────────────────────────────

    def create_user_account(
        self,
        username: str,
        password: str,
        role: str,
        full_name: str,
        teacher_id: int | None = None,
        must_change: bool = True,
    ) -> int:
        """Create a new user account. Caller must have settings.users permission."""
        self._require_permission("settings.users")

        # Head teachers can only create class_teacher / subject_teacher
        if self._session.is_head_teacher and role not in ("class_teacher", "subject_teacher"):
            raise ServiceError(
                "Head teachers can only create Class Teacher or Subject Teacher accounts."
            )

        if not username.strip():
            raise ServiceError("Username is required.")
        if not password or len(password) < 6:
            raise ServiceError("Password must be at least 6 characters.")

        exists = fetch_one("SELECT id FROM users WHERE username=?", (username.strip(),))
        if exists:
            raise ServiceError(f"Username '{username}' already exists.")

        uid = create_user(
            username.strip(), password, role, full_name.strip(),
            teacher_id=teacher_id, must_change=must_change
        )
        self._audit("user_created", "users", uid,
                    detail=f"Created {role} account: {username}")
        return uid

    def deactivate_user(self, user_id: int) -> None:
        self._require_permission("settings.users")

        target = fetch_one("SELECT * FROM users WHERE id=?", (user_id,))
        if not target:
            raise ServiceError("User not found.")

        # Head teachers cannot deactivate admin accounts
        if self._session.is_head_teacher and target["role"] in ("admin", "head_teacher"):
            raise ServiceError("Head teachers cannot deactivate Admin or Head Teacher accounts.")

        if user_id == self._session.user_id:
            raise ServiceError("You cannot deactivate your own account.")

        execute("UPDATE users SET is_active=0 WHERE id=?", (user_id,))
        self._audit("user_deactivated", "users", user_id,
                    detail=f"Deactivated: {target['username']}",
                    before={"is_active": 1}, after={"is_active": 0})

    # ── Policy override management ────────────────────────────────────────────

    def grant_policy_override(
        self,
        rule_name: str,
        entity_type: str,
        entity_id: int,
        decision: str,   # "allow" | "deny"
        reason: str = "",
        expires_at: str | None = None,
    ) -> int:
        """
        Persist a policy override to the DB and load it into the engine.
        Only admins may grant overrides.
        """
        if not self._session.is_admin:
            raise ServiceError("Only administrators can grant policy overrides.")
        if decision not in ("allow", "deny"):
            raise ServiceError("Decision must be 'allow' or 'deny'.")

        ov_id = execute(
            """INSERT OR REPLACE INTO policy_overrides
               (policy_rule, entity_type, entity_id, decision, reason, granted_by, expires_at)
               VALUES (?,?,?,?,?,?,?)""",
            (rule_name, entity_type, entity_id, decision,
             reason, self._session.user_id, expires_at),
        )
        from policy.engine import policy_engine
        policy_engine.add_override(rule_name, entity_type, entity_id, decision)
        self._audit("policy_override_granted", "policy_overrides", ov_id,
                    detail=f"{decision} {rule_name} for {entity_type}:{entity_id}")
        return ov_id


# Singleton
auth_service = AuthService()
