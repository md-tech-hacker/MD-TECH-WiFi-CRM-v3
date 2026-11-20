"""SQLite data layer. All timestamps are stored as UTC ISO-8601 strings."""
from __future__ import annotations

import contextlib
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.getenv('MDTECH_DATA_DIR', str(ROOT / 'instance')))
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / 'mdtech.sqlite3'


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@contextlib.contextmanager
def db():
    conn = sqlite3.connect(DB_PATH, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys=ON')
    conn.execute('PRAGMA busy_timeout=20000')
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def row(r):
    return dict(r) if r is not None else None


def rows(result):
    return [dict(r) for r in result]


def setting(conn, key: str, default: str = '') -> str:
    r = conn.execute('SELECT value FROM settings WHERE key=?', (key,)).fetchone()
    return r['value'] if r else default


def put_setting(conn, key: str, value: str) -> None:
    conn.execute('INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value', (key, value))


def log(conn, action, detail='', actor='system', category='system'):
    conn.execute('INSERT INTO activity(created_at, actor, category, action, detail) VALUES (?,?,?,?,?)', (now(), actor, category, action, str(detail)[:700]))


def init_db():
    with db() as conn:
        conn.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS admins (
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT NOT NULL UNIQUE,
          password_hash TEXT NOT NULL, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS admin_sessions (
          id INTEGER PRIMARY KEY AUTOINCREMENT, admin_id INTEGER NOT NULL REFERENCES admins(id) ON DELETE CASCADE,
          token_hash TEXT NOT NULL UNIQUE, csrf TEXT NOT NULL, expires_at TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
          display_name TEXT NOT NULL, password_hash TEXT NOT NULL,
          email TEXT DEFAULT '', enabled INTEGER DEFAULT 1,
          created_at TEXT NOT NULL, last_login_at TEXT
        );
        CREATE TABLE IF NOT EXISTS vouchers (
          id INTEGER PRIMARY KEY AUTOINCREMENT, code_hash TEXT UNIQUE NOT NULL,
          code_hint TEXT NOT NULL, label TEXT DEFAULT '', duration_minutes INTEGER NOT NULL,
          data_limit_mb INTEGER DEFAULT 0, max_uses INTEGER NOT NULL DEFAULT 1,
          used_count INTEGER NOT NULL DEFAULT 0, enabled INTEGER NOT NULL DEFAULT 1,
          expires_at TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS devices (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          mac TEXT UNIQUE NOT NULL, name TEXT NOT NULL DEFAULT '',
          ip TEXT NOT NULL DEFAULT '', owner_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
          blocked INTEGER NOT NULL DEFAULT 0, source TEXT NOT NULL DEFAULT 'manual',
          first_seen TEXT NOT NULL, last_seen TEXT NOT NULL,
          rx_bytes INTEGER NOT NULL DEFAULT 0, tx_bytes INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS guest_sessions (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
          voucher_id INTEGER REFERENCES vouchers(id) ON DELETE SET NULL,
          device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL,
          client_ip TEXT NOT NULL DEFAULT '', login_method TEXT NOT NULL,
          started_at TEXT NOT NULL, expires_at TEXT NOT NULL,
          ended_at TEXT, state TEXT NOT NULL DEFAULT 'authorized',
          gateway_verified INTEGER NOT NULL DEFAULT 0,
          rx_bytes INTEGER NOT NULL DEFAULT 0, tx_bytes INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS policies (
          id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL,
          kind TEXT NOT NULL CHECK(kind IN ('domain','app','ip','device')),
          target TEXT NOT NULL, action TEXT NOT NULL CHECK(action IN ('block','allow')),
          scope_type TEXT NOT NULL DEFAULT 'all' CHECK(scope_type IN ('all','user','device')),
          scope_id INTEGER, enabled INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS activity (
          id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
          actor TEXT NOT NULL, category TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS traffic (
          id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
          device_id INTEGER REFERENCES devices(id) ON DELETE SET NULL,
          rx_bytes INTEGER NOT NULL DEFAULT 0, tx_bytes INTEGER NOT NULL DEFAULT 0,
          blocked INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS ix_session_active ON guest_sessions(state, expires_at);
        CREATE INDEX IF NOT EXISTS ix_activity_date ON activity(created_at);
        CREATE INDEX IF NOT EXISTS ix_traffic_date ON traffic(created_at);
        ''')
        # Upgrade older local databases without deleting any existing data.
        columns = [c['name'] for c in conn.execute('PRAGMA table_info(guest_sessions)')]
        if 'gateway_verified' not in columns:
            conn.execute('ALTER TABLE guest_sessions ADD COLUMN gateway_verified INTEGER NOT NULL DEFAULT 0')
        if 'bind_token_hash' not in columns:
            conn.execute("ALTER TABLE guest_sessions ADD COLUMN bind_token_hash TEXT NOT NULL DEFAULT ''")
        defaults = {
            'site_name': 'MD TECH', 'ssid': '', 'portal_title': 'Welcome to MD TECH Wi-Fi',
            'portal_message': 'Connect securely using your account or access code.',
            'gateway_enabled': '0', 'gateway_key_hash': '', 'gateway_label': 'Not connected'
        }
        for k, v in defaults.items():
            conn.execute('INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)', (k, v))
