"""Password hashing, opaque session cookies, voucher HMACs, and basic rate limiting."""
from __future__ import annotations
import hashlib
import hmac
import os
import secrets
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from .db import DATA_DIR


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.scrypt(password.encode(), salt=salt, n=2**14, r=8, p=1, dklen=32)
    return f'scrypt$16384$8$1${salt.hex()}${key.hex()}'


def verify_password(password: str, encoded: str) -> bool:
    try:
        scheme, n, r, p, salt, digest = encoded.split('$')
        if scheme != 'scrypt': return False
        expected = hashlib.scrypt(password.encode(), salt=bytes.fromhex(salt), n=int(n), r=int(r), p=int(p), dklen=32)
        return hmac.compare_digest(expected, bytes.fromhex(digest))
    except (ValueError, TypeError):
        return False


def token_hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def new_token() -> str:
    return secrets.token_urlsafe(36)


def utc_after(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat(timespec='seconds')


_voucher_secret: bytes | None = None
_voucher_lock = Lock()


def voucher_digest(code: str) -> str:
    global _voucher_secret
    if _voucher_secret is None:
        with _voucher_lock:
            if _voucher_secret is None:
                secret_file = DATA_DIR / 'voucher_secret.key'
                if not secret_file.exists():
                    fd = os.open(secret_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
                    with os.fdopen(fd, 'wb') as f:
                        f.write(secrets.token_bytes(32))
                _voucher_secret = secret_file.read_bytes()
    return hmac.new(_voucher_secret, code.strip().upper().encode(), hashlib.sha256).hexdigest()


_attempts = defaultdict(deque)
_attempts_lock = Lock()
def rate_allowed(key: str, limit=8, window=300) -> bool:
    now = time.monotonic()
    with _attempts_lock:
        if len(_attempts) >= 4096:
            for stale in list(_attempts):
                if not _attempts[stale] or now - _attempts[stale][-1] > 3600:
                    del _attempts[stale]
            if key not in _attempts and len(_attempts) >= 4096:
                return False
        q = _attempts[key]
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= limit:
            return False
        q.append(now)
        return True
