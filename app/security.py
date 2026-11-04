"""Password hashing, JWT handling, rate limiting and RBAC decorators."""
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import current_app, g, request
from werkzeug.security import check_password_hash, generate_password_hash

from .errors import ApiError

ALGORITHM = "HS256"
ISSUER = "sgcm-api"
AUDIENCE = "sgcm-clients"
ROLES = ("ADMIN", "USER")
# Pre-computed hash used to equalize timing for unknown users (API2)
_DUMMY_HASH = generate_password_hash("dummy-password-for-timing")


def hash_password(password):
    return generate_password_hash(password)


def verify_password(password, password_hash):
    return check_password_hash(password_hash or _DUMMY_HASH, password) and bool(password_hash)


def create_token(user_id, username, role, secret, ttl_minutes, now=None):
    now = now or datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "iss": ISSUER,
        "aud": AUDIENCE,
        "iat": now,
        "exp": now + timedelta(minutes=ttl_minutes),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, secret, algorithm=ALGORITHM)


def decode_token(token, secret):
    """Decode pinning the algorithm and requiring the critical claims."""
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            issuer=ISSUER,
            audience=AUDIENCE,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.PyJWTError:
        raise ApiError(401, "Invalid or expired token") from None


class RateLimiter:
    """Sliding-window limiter counting failed attempts per key."""

    def __init__(self, limit, window_seconds, clock=time.monotonic):
        self.limit = limit
        self.window = window_seconds
        self.clock = clock
        self._events = defaultdict(deque)

    def _purge(self, key):
        events = self._events[key]
        cutoff = self.clock() - self.window
        while events and events[0] <= cutoff:
            events.popleft()
        return events

    def allow(self, key):
        return len(self._purge(key)) < self.limit

    def fail(self, key):
        self._purge(key).append(self.clock())

    def reset(self, key):
        self._events.pop(key, None)


def _bearer_token():
    header = request.headers.get("Authorization", "")
    scheme, _, token = header.partition(" ")
    if scheme != "Bearer" or not token:
        raise ApiError(401, "Missing bearer token")
    return token.strip()


def require_roles(*roles):
    """RBAC (API5, broken function level authorization)."""

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            claims = decode_token(_bearer_token(), current_app.config["JWT_SECRET"])
            if claims.get("role") not in ROLES:
                raise ApiError(401, "Invalid or expired token")
            if roles and claims["role"] not in roles:
                raise ApiError(403, "Forbidden")
            g.current_user = {
                "id": int(claims["sub"]),
                "username": claims.get("username"),
                "role": claims["role"],
            }
            return fn(*args, **kwargs)

        return wrapper

    return decorator
