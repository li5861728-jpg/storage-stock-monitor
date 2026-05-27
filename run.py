#!/usr/bin/env python3
"""一键启动：初始化数据库 + 运行一次爬虫 + 启动 Web 服务"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import init_db, save_events
from scraper.eastmoney import fetch_sector_news, fetch_market_data
from scraper.cls import fetch_telegraph
from scraper.jiwei import fetch_news


def main():
    print("=" * 50)
    print("  A股存储板块 · 信息聚合系统")
    print("=" * 50)

    # 1. 初始化数据库
    print("\n[1/3] 初始化数据库...")
    init_db()

    # 2. 运行爬虫
    print("\n[2/3] 开始抓取数据...")
    all_scrapers = [
        ("财联社快讯", fetch_telegraph),
        ("东方财富公告", fetch_sector_news),
        ("东方财富行情", fetch_market_data),
        ("集微网行业新闻", fetch_news),
    ]

    total_saved = 0
    for name, fetcher in all_scrapers:
        try:
            print(f"  [{name}] 抓取中...", end=" ")
            events = fetcher()
            saved = save_events(events)
            total_saved += saved
            print(f"获取 {len(events)} 条, 新增 {saved} 条")
        except Exception as e:
            print(f"失败: {e}")
        time.sleep(0.5)

    print(f"\n  总计新增 {total_saved} 条事件")

    # 3. 启动 Web 服务
    print("\n[3/3] 启动 Web 服务 → http://localhost:8080")
    print("  按 Ctrl+C 停止服务\n")

    from web.app import app
    app.run(host="0.0.0.0", port=8080, debug=False)


if __name__ == "__main__":
    main()
