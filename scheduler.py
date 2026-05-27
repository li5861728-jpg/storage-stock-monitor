"""定时抓取调度器 - 可独立进程运行"""

import time
import schedule

from database import init_db, save_events
from scraper.eastmoney import fetch_sector_news, fetch_market_data
from scraper.cls import fetch_telegraph
from scraper.jiwei import fetch_news


def run_all_scrapers():
    """执行所有爬虫并保存结果"""
    print(f"\n{'='*50}")
    print(f"[调度器] 开始抓取 {time.strftime('%Y-%m-%d %H:%M:%S')} Beijing")
    total_saved = 0

    scrapers = [
        ("财联社快讯", fetch_telegraph),
        ("东方财富公告", fetch_sector_news),
        ("东方财富行情", fetch_market_data),
        ("集微网行业", fetch_news),
    ]

    for name, fetcher in scrapers:
        try:
            print(f"  [{name}]", end=" ")
            events = fetcher()
            saved = save_events(events)
            total_saved += saved
            print(f"{len(events)} 条 / 新增 {saved}")
        except Exception as e:
            print(f"错误: {e}")

    print(f"[调度器] 完成, 新增 {total_saved}")
    print(f"{'='*50}\n")


def main():
    init_db()
    print("[调度器] 启动定时抓取...")

    # 首次立即执行
    run_all_scrapers()

    # 定时任务
    schedule.every(5).minutes.do(fetch_telegraph)       # 财联社快讯 5分钟
    schedule.every(1).hours.do(fetch_sector_news)       # 东财公告 1小时
    schedule.every(1).hours.do(fetch_market_data)       # 东财行情 1小时
    schedule.every(1).hours.do(fetch_news)              # 集微网 1小时

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == "__main__":
    main()
