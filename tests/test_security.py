from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.errors import ApiError
from app import security as s

SECRET = "x" * 40


def test_hash_and_verify():
    h = s.hash_password("Passw0rdSegura")
    assert h != "Passw0rdSegura"
    assert s.verify_password("Passw0rdSegura", h) is True
    assert s.verify_password("otra", h) is False
    assert s.verify_password("Passw0rdSegura", None) is False
    assert s.verify_password("dummy-password-for-timing", None) is False


def test_token_roundtrip():
    tok = s.create_token(7, "ana", "USER", SECRET, 15)
    claims = s.decode_token(tok, SECRET)
    assert claims["sub"] == "7" and claims["role"] == "USER"
    assert claims["username"] == "ana"
    assert claims["iss"] == s.ISSUER and claims["aud"] == s.AUDIENCE
    assert claims["exp"] - claims["iat"] == 15 * 60
    assert len(claims["jti"]) == 32


def test_tokens_have_unique_jti():
    a = s.decode_token(s.create_token(1, "a", "USER", SECRET, 5), SECRET)
    b = s.decode_token(s.create_token(1, "a", "USER", SECRET, 5), SECRET)
    assert a["jti"] != b["jti"]


def test_expired_token_rejected():
    old = datetime.now(timezone.utc) - timedelta(hours=1)
    tok = s.create_token(1, "a", "USER", SECRET, 5, now=old)
    with pytest.raises(ApiError) as e:
        s.decode_token(tok, SECRET)
    assert e.value.status == 401


def test_wrong_secret_rejected():
    tok = s.create_token(1, "a", "USER", SECRET, 5)
    with pytest.raises(ApiError):
        s.decode_token(tok, "y" * 40)


def test_alg_none_rejected():
    now = datetime.now(timezone.utc)
    payload = {"sub": "1", "role": "ADMIN", "iss": s.ISSUER, "aud": s.AUDIENCE,
               "iat": now, "exp": now + timedelta(minutes=5)}
    tok = jwt.encode(payload, None, algorithm="none")
    with pytest.raises(ApiError):
        s.decode_token(tok, SECRET)


@pytest.mark.parametrize("missing", ["exp", "iat", "sub", "iss", "aud"])
def test_missing_claims_rejected(missing):
    now = datetime.now(timezone.utc)
    payload = {"sub": "1", "role": "USER", "iss": s.ISSUER, "aud": s.AUDIENCE,
               "iat": now, "exp": now + timedelta(minutes=5)}
    payload.pop(missing)
    tok = jwt.encode(payload, SECRET, algorithm="HS256")
    with pytest.raises(ApiError):
        s.decode_token(tok, SECRET)


def test_wrong_issuer_and_audience_rejected():
    now = datetime.now(timezone.utc)
    base = {"sub": "1", "role": "USER", "iat": now, "exp": now + timedelta(minutes=5)}
    for extra in ({"iss": "evil", "aud": s.AUDIENCE}, {"iss": s.ISSUER, "aud": "other"}):
        tok = jwt.encode({**base, **extra}, SECRET, algorithm="HS256")
        with pytest.raises(ApiError):
            s.decode_token(tok, SECRET)


def test_garbage_token_rejected():
    with pytest.raises(ApiError):
        s.decode_token("not.a.jwt", SECRET)


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_rate_limiter_blocks_after_limit():
    clk = Clock()
    rl = s.RateLimiter(3, 60, clock=clk)
    for _ in range(3):
        assert rl.allow("k")
        rl.fail("k")
    assert not rl.allow("k")
    assert rl.allow("other")


def test_rate_limiter_window_expiry():
    clk = Clock()
    rl = s.RateLimiter(2, 60, clock=clk)
    rl.fail("k")
    rl.fail("k")
    assert not rl.allow("k")
    clk.t += 59.9
    assert not rl.allow("k")
    clk.t += 0.1  # exactly window -> expired
    assert rl.allow("k")


def test_rate_limiter_partial_expiry_and_reset():
    clk = Clock()
    rl = s.RateLimiter(2, 60, clock=clk)
    rl.fail("k")
    clk.t += 40
    rl.fail("k")
    assert not rl.allow("k")
    clk.t += 30  # first expired, second alive
    assert rl.allow("k")
    rl.fail("k")
    assert not rl.allow("k")
    rl.reset("k")
    assert rl.allow("k")
    rl.reset("never-seen")
