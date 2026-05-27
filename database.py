"""数据库操作层"""

import json
import sqlite3
import os
from config import DB_PATH, DATA_DIR
from timezone import beijing_now


def get_db():
    """获取数据库连接"""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT,
            source TEXT NOT NULL,
            source_url TEXT,
            published_at TEXT NOT NULL,
            fetched_at TEXT DEFAULT (datetime('now','localtime')),
            stocks TEXT,
            stock_names TEXT,
            bullish_pct INTEGER DEFAULT 50,
            bearish_pct INTEGER DEFAULT 50,
            sentiment TEXT DEFAULT 'neutral',
            keywords_matched TEXT
        )
    """)
    # 去重索引
    conn.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_dedup
        ON events(source, source_url)
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_published ON events(published_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_sentiment ON events(sentiment)")
    conn.commit()
    conn.close()


def save_events(events: list[dict]) -> int:
    """保存事件，返回新增数量"""
    conn = get_db()
    saved = 0
    for evt in events:
        try:
            before = conn.total_changes
            conn.execute(
                """INSERT OR IGNORE INTO events
                (title, summary, source, source_url, published_at, fetched_at,
                 stocks, stock_names, bullish_pct, bearish_pct, sentiment, keywords_matched)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    evt["title"],
                    evt.get("summary", ""),
                    evt["source"],
                    evt.get("source_url", ""),
                    evt["published_at"],
                    beijing_now(),
                    json.dumps(evt.get("stocks", []), ensure_ascii=False),
                    json.dumps(evt.get("stock_names", []), ensure_ascii=False),
                    evt.get("bullish_pct", 50),
                    evt.get("bearish_pct", 50),
                    evt.get("sentiment", "neutral"),
                    json.dumps(evt.get("keywords_matched", []), ensure_ascii=False),
                ),
            )
            if conn.total_changes > before:
                saved += 1
        except Exception as e:
            print(f"[DB] 插入失败: {e}")

    conn.commit()
    conn.close()
    return saved


def get_events(date: str = None, sentiment: str = None, keyword: str = None,
               page: int = 1, page_size: int = 50) -> list[dict]:
    """查询事件，支持按日期/情绪/关键词筛选"""
    conn = get_db()
    conditions = []
    params = []

    if date:
        conditions.append("date(published_at) = ?")
        params.append(date)
    if sentiment and sentiment != "all":
        conditions.append("sentiment = ?")
        params.append(sentiment)
    if keyword:
        conditions.append("(title LIKE ? OR summary LIKE ?)")
        params.extend([f"%{keyword}%", f"%{keyword}%"])

    where = " WHERE " + " AND ".join(conditions) if conditions else ""
    offset = (page - 1) * page_size

    rows = conn.execute(
        f"""SELECT * FROM events{where}
        ORDER BY published_at DESC
        LIMIT ? OFFSET ?""",
        params + [page_size, offset],
    ).fetchall()

    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_dates() -> list[str]:
    """获取有数据的日期列表"""
    conn = get_db()
    rows = conn.execute(
        "SELECT DISTINCT date(published_at) as d FROM events ORDER BY d DESC LIMIT 60"
    ).fetchall()
    conn.close()
    return [r["d"] for r in rows]


def get_stats(date: str = None) -> dict:
    """获取统计信息"""
    conn = get_db()
    if date:
        base = "WHERE date(published_at) = ?"
        params = [date]
    else:
        base = ""
        params = []

    def _count(extra):
        where = f"{base} {extra}" if base else f"WHERE {extra}"
        return conn.execute(f"SELECT COUNT(*) as c FROM events {where}", params).fetchone()["c"]

    total = conn.execute(f"SELECT COUNT(*) as c FROM events {base}", params).fetchone()["c"]
    bullish = _count("sentiment='bullish'")
    bearish = _count("sentiment='bearish'")
    neutral = _count("sentiment='neutral'")

    sources = conn.execute(
        f"SELECT source, COUNT(*) as c FROM events {base} GROUP BY source", params
    ).fetchall() if base else conn.execute(
        "SELECT source, COUNT(*) as c FROM events GROUP BY source"
    ).fetchall()

    conn.close()
    return {
        "total": total,
        "bullish": bullish,
        "bearish": bearish,
        "neutral": neutral,
        "by_source": {r["source"]: r["c"] for r in sources},
    }


def _row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "summary": row["summary"],
        "source": row["source"],
        "source_url": row["source_url"],
        "published_at": row["published_at"],
        "stocks": json.loads(row["stocks"]) if row["stocks"] else [],
        "stock_names": json.loads(row["stock_names"]) if row["stock_names"] else [],
        "bullish_pct": row["bullish_pct"],
        "bearish_pct": row["bearish_pct"],
        "sentiment": row["sentiment"],
        "keywords_matched": json.loads(row["keywords_matched"]) if row["keywords_matched"] else [],
    }
