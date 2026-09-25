"""Sign-in, sessions, throttling and building the request principal."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from optiedt.config import Settings
from optiedt.errors import FieldError, InvalidInput, TooManyRequests, Unauthenticated
from optiedt.models import Department, LoginThrottle, User, UserSession
from optiedt.security import passwords, tokens
from optiedt.security.permissions import Principal
from optiedt.services import audit

IP_FAILURE_MULTIPLIER = 4
"""A client address may fail this many times more often than one account before lockout."""

TOUCH_INTERVAL = timedelta(seconds=60)


def _now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class LoginResult:
    user: User
    token: str
    session: UserSession


def _throttle_check(db: Session, key: str, now: datetime) -> None:
    row = db.get(LoginThrottle, key)
    if row and row.locked_until and row.locked_until > now:
        wait = int((row.locked_until - now).total_seconds()) + 1
        raise TooManyRequests(
            "Too many failed sign-in attempts. Try again later.", retry_after_seconds=wait
        )


def _throttle_fail(db: Session, key: str, limit: int, settings: Settings, now: datetime) -> None:
    window = timedelta(minutes=settings.login_window_minutes)
    row = db.get(LoginThrottle, key)
    if row is None:
        row = LoginThrottle(key=key, failures=0, window_started_at=now)
        db.add(row)
    if now - row.window_started_at > window:
        row.failures = 0
        row.window_started_at = now
        row.locked_until = None
    row.failures += 1
    if row.failures >= limit:
        row.locked_until = now + timedelta(minutes=settings.login_lockout_minutes)


def _throttle_clear(db: Session, key: str) -> None:
    row = db.get(LoginThrottle, key)
    if row is not None:
        db.delete(row)


def normalise_username(username: str) -> str:
    return username.strip().lower()


def login(
    db: Session,
    settings: Settings,
    *,
    username: str,
    password: str,
    ip_address: str | None,
    user_agent: str | None,
) -> LoginResult:
    now = _now()
    name = normalise_username(username)
    user_key = f"user:{name}"
    ip_key = f"ip:{ip_address or 'unknown'}"
    _throttle_check(db, user_key, now)
    _throttle_check(db, ip_key, now)

    user = db.scalar(select(User).where(User.username == name))
    valid = passwords.verify_password(password, user.password_hash if user else None)
    if not valid or user is None or not user.is_active:
        _throttle_fail(db, user_key, settings.login_max_failures, settings, now)
        _throttle_fail(
            db, ip_key, settings.login_max_failures * IP_FAILURE_MULTIPLIER, settings, now
        )
        db.commit()
        raise Unauthenticated("The username or password is incorrect.")

    _throttle_clear(db, user_key)
    if user.password_hash and passwords.needs_rehash(user.password_hash):
        user.password_hash = passwords.hash_password(password)

    token = tokens.new_token()
    session = UserSession(
        user_id=user.id,
        token_hash=tokens.digest(token),
        csrf_token=tokens.new_token(),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=settings.session_absolute_hours),
        ip_address=(ip_address or "")[:64] or None,
        user_agent=(user_agent or "")[:256] or None,
    )
    db.add(session)
    user.last_login_at = now
    principal = build_principal(db, user)
    audit.record(
        db,
        principal,
        action="auth.login",
        entity_type="user",
        entity_id=user.id,
        summary=f"{user.username} signed in",
    )
    return LoginResult(user=user, token=token, session=session)


def resolve_session(
    db: Session, settings: Settings, token: str | None
) -> tuple[User, UserSession] | None:
    if not token:
        return None
    now = _now()
    session = db.scalar(select(UserSession).where(UserSession.token_hash == tokens.digest(token)))
    if session is None or session.revoked_at is not None or session.expires_at <= now:
        return None
    if now - session.last_seen_at > timedelta(minutes=settings.session_idle_minutes):
        return None
    user = db.get(User, session.user_id)
    if user is None or not user.is_active:
        return None
    if now - session.last_seen_at > TOUCH_INTERVAL:
        # A plain UPDATE: touching the session must not bump the user's version or collide
        # with concurrent edits of the same session row.
        db.execute(update(UserSession).where(UserSession.id == session.id).values(last_seen_at=now))
    return user, session


def logout(db: Session, session: UserSession, principal: Principal) -> None:
    session.revoked_at = _now()
    audit.record(
        db,
        principal,
        action="auth.logout",
        entity_type="user",
        entity_id=principal.user_id,
        summary=f"{principal.username} signed out",
    )


def department_parents(db: Session) -> dict[uuid.UUID, uuid.UUID | None]:
    rows = db.execute(select(Department.id, Department.parent_id)).all()
    return {row[0]: row[1] for row in rows}


def build_principal(db: Session, user: User) -> Principal:
    return Principal.build(
        user_id=user.id,
        username=user.username,
        display_name=user.display_name,
        roles=[(r.role, r.department_id) for r in user.roles],
        instructor_id=user.instructor_id,
        parent_of=department_parents(db),
    )


def change_password(
    db: Session,
    user: User,
    principal: Principal,
    *,
    current: str,
    new: str,
    keep_session_id: uuid.UUID | None,
) -> None:
    if not passwords.verify_password(current, user.password_hash):
        raise InvalidInput(
            "The current password is incorrect.",
            [FieldError("current_password", "Incorrect password.")],
        )
    problems = passwords.policy_violations(new, username=user.username)
    if problems:
        raise InvalidInput(
            "The new password does not meet the policy.",
            [FieldError("new_password", p) for p in problems],
        )
    now = _now()
    user.password_hash = passwords.hash_password(new)
    user.password_changed_at = now
    user.must_change_password = False
    # Every other session of this user ends with the old password.
    db.execute(
        update(UserSession)
        .where(
            UserSession.user_id == user.id,
            UserSession.revoked_at.is_(None),
            UserSession.id != keep_session_id,
        )
        .values(revoked_at=now)
    )
    audit.record(
        db,
        principal,
        action="auth.password_changed",
        entity_type="user",
        entity_id=user.id,
        summary=f"{user.username} changed their password",
    )
