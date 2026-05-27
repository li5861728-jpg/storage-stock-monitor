"""集微网(laoyaoba.com) - 存储芯片产业链新闻抓取"""

import requests
from bs4 import BeautifulSoup
from config import HEADERS
from analyzer.scorer import score_text
from timezone import beijing_now

FILTER_KEYWORDS = [
    "存储", "NAND", "DRAM", "闪存", "内存", "芯片",
    "HBM", "高带宽", "存储器", "SSD", "eMMC", "UFS",
    "半导体", "晶圆", "封测",
]


def fetch_news() -> list[dict]:
    """抓取集微网/老杳吧半导体新闻"""
    events = []
    try:
        # 使用HTTP避免SSL兼容性问题
        resp = requests.get(
            "http://www.laoyaoba.com/",
            headers={**HEADERS, "Referer": "https://www.laoyaoba.com/"},
            timeout=15,
        )
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")

        links = soup.find_all("a", href=True)
        seen = set()

        for link in links:
            title = link.get_text(strip=True)
            href = link.get("href", "")

            if not title or len(title) < 6:
                continue
            if not _is_storage_related(title):
                continue
            if href in seen:
                continue
            seen.add(href)

            # 构建完整URL
            if href.startswith("/"):
                href = "https://www.laoyaoba.com" + href
            elif not href.startswith("http"):
                continue

            # 尝试提取摘要（在父元素中查找）
            parent = link.parent
            summary = ""
            if parent:
                p = parent.find("p") or parent.find(class_="desc") or parent.find(class_="summary")
                if p:
                    summary = p.get_text(strip=True)

            score = score_text(title, summary)

            events.append({
                "title": title,
                "summary": summary or title,
                "source": "jiwei",
                "source_url": href,
                "published_at": beijing_now(),
                "stocks": [],
                "stock_names": [],
                **score,
            })

            if len(events) >= 15:
                break

    except Exception as e:
        print(f"[集微网] 抓取失败: {e}")

    return events


def _is_storage_related(title: str) -> bool:
    return any(kw.lower() in title.lower() for kw in FILTER_KEYWORDS)
