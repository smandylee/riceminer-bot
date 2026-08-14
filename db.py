import sqlite3
import time

import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS sites (
    code TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 1,
    interval_sec INTEGER NOT NULL DEFAULT 180
);

CREATE TABLE IF NOT EXISTS seen_posts (
    site_code TEXT NOT NULL,
    post_url TEXT NOT NULL,
    seen_at INTEGER NOT NULL,
    UNIQUE(site_code, post_url)
);

CREATE TABLE IF NOT EXISTS bot_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    post_channel_id INTEGER,
    log_channel_id INTEGER
);
"""


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA)
    for code in config.SITE_CODES:
        conn.execute(
            "INSERT OR IGNORE INTO sites (code, enabled, interval_sec) VALUES (?, 1, ?)",
            (code, config.DEFAULT_INTERVAL_SEC),
        )
    conn.execute("INSERT OR IGNORE INTO bot_settings (id) VALUES (1)")
    conn.commit()


def get_settings(conn: sqlite3.Connection) -> sqlite3.Row:
    conn.row_factory = sqlite3.Row
    return conn.execute("SELECT * FROM bot_settings WHERE id = 1").fetchone()


def set_post_channel(conn: sqlite3.Connection, channel_id: int) -> None:
    conn.execute("UPDATE bot_settings SET post_channel_id = ? WHERE id = 1", (channel_id,))
    conn.commit()


def set_log_channel(conn: sqlite3.Connection, channel_id: int) -> None:
    conn.execute("UPDATE bot_settings SET log_channel_id = ? WHERE id = 1", (channel_id,))
    conn.commit()


def get_site(conn: sqlite3.Connection, code: str) -> sqlite3.Row | None:
    conn.row_factory = sqlite3.Row
    return conn.execute("SELECT * FROM sites WHERE code = ?", (code,)).fetchone()


def list_sites(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    conn.row_factory = sqlite3.Row
    return conn.execute("SELECT * FROM sites ORDER BY code").fetchall()


def set_enabled(conn: sqlite3.Connection, code: str, enabled: bool) -> None:
    conn.execute("UPDATE sites SET enabled = ? WHERE code = ?", (int(enabled), code))
    conn.commit()


def set_interval(conn: sqlite3.Connection, code: str, seconds: int) -> None:
    if seconds < config.MIN_INTERVAL_SEC:
        raise ValueError(
            f"interval은 최소 {config.MIN_INTERVAL_SEC}초 이상이어야 합니다 (요청: {seconds}초)"
        )
    conn.execute("UPDATE sites SET interval_sec = ? WHERE code = ?", (seconds, code))
    conn.commit()


def is_seen(conn: sqlite3.Connection, site_code: str, post_url: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM seen_posts WHERE site_code = ? AND post_url = ?",
        (site_code, post_url),
    ).fetchone()
    return row is not None


def mark_seen(conn: sqlite3.Connection, site_code: str, post_url: str) -> None:
    conn.execute(
        "INSERT OR IGNORE INTO seen_posts (site_code, post_url, seen_at) VALUES (?, ?, ?)",
        (site_code, post_url, int(time.time())),
    )
    conn.commit()
