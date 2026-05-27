"""Flask Web 应用"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, jsonify, request, render_template
from database import init_db, get_events, get_dates, get_stats, get_db, _row_to_dict
from timezone import beijing_now

app = Flask(__name__)

SOURCE_LABELS = {
    "cninfo": "巨潮资讯网",
    "eastmoney": "东方财富",
    "cls": "财联社",
    "jiwei": "集微网",
}


@app.route("/")
def index():
    return render_template("index.html", source_labels=SOURCE_LABELS)


@app.route("/api/events")
def api_events():
    date = request.args.get("date")
    sentiment = request.args.get("sentiment")
    keyword = request.args.get("keyword")
    page = request.args.get("page", 1, type=int)

    events = get_events(date=date, sentiment=sentiment, keyword=keyword, page=page)

    # 按日分组
    grouped = {}
    for evt in events:
        day = evt["published_at"][:10]
        if day not in grouped:
            grouped[day] = []
        grouped[day].append(evt)

    return jsonify({
        "events": events,
        "grouped": grouped,
        "days": sorted(grouped.keys(), reverse=True),
        "page": page,
    })


@app.route("/api/dates")
def api_dates():
    return jsonify({"dates": get_dates()})


@app.route("/api/stats")
def api_stats():
    date = request.args.get("date")
    return jsonify(get_stats(date=date))


@app.route("/api/latest")
def api_latest():
    """返回最新事件（供前端轮询），支持增量更新"""
    since = request.args.get("since", "")

    conn = get_db()
    params = []
    if since:
        rows = conn.execute(
            "SELECT * FROM events WHERE published_at > ? ORDER BY published_at DESC LIMIT 50",
            [since],
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM events ORDER BY published_at DESC LIMIT 30"
        ).fetchall()
    conn.close()

    events = [_row_to_dict(r) for r in rows]

    grouped = {}
    for evt in events:
        day = evt["published_at"][:10]
        if day not in grouped:
            grouped[day] = []
        grouped[day].append(evt)

    return jsonify({
        "events": events,
        "grouped": grouped,
        "days": sorted(grouped.keys(), reverse=True),
        "server_time": beijing_now(),
        "count": len(events),
    })


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=8080, debug=True)
