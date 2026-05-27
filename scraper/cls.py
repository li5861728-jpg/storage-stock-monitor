"""财联社 - 电报快讯抓取（解析电报页面）"""

import json
import re
import requests
from bs4 import BeautifulSoup
from config import HEADERS
from analyzer.scorer import score_text
from timezone import beijing_now

FILTER_KEYWORDS = [
    "存储", "NAND", "DRAM", "闪存", "内存", "芯片", "半导体",
    "集成电路", "封测", "晶圆", "HBM", "高带宽", "存储器",
    "SSD", "eMMC", "UFS", "中芯国际", "兆易创新", "江波龙",
    "佰维存储", "北京君正", "澜起科技", "长电科技", "通富微电",
    "华天科技", "紫光国微", "复旦微电", "东芯股份", "长江存储",
    "长鑫存储", "寒武纪", "全志科技", "华大九天", "SK海力士",
    "三星", "美光", "铠侠", "西数", "西部数据", "闻泰科技",
]

STOCK_NAMES = [
    "中芯国际", "兆易创新", "江波龙", "佰维存储", "北京君正",
    "澜起科技", "长电科技", "通富微电", "华天科技", "紫光国微",
    "复旦微电", "东芯股份", "寒武纪", "全志科技", "华大九天",
    "聚辰股份", "长江存储", "长鑫存储", "闻泰科技",
]


def fetch_telegraph() -> list[dict]:
    """从财联社电报页面抓取存储相关快讯"""
    events = []
    try:
        resp = requests.get(
            "https://www.cls.cn/telegraph",
            headers={**HEADERS, "Referer": "https://www.cls.cn/"},
            timeout=15,
        )
        resp.encoding = "utf-8"
        soup = BeautifulSoup(resp.text, "lxml")

        # 在 script 标签中找 Next.js 数据
        data = None
        for script in soup.find_all("script"):
            if script.string and "telegraphList" in script.string:
                match = re.search(r'\{.*\}', script.string, re.DOTALL)
                if match:
                    try:
                        data = json.loads(match.group())
                    except json.JSONDecodeError:
                        continue
                    break

        if not data:
            print("[财联社] 未找到电报数据")
            return events

        items = data["props"]["initialState"]["telegraph"]["telegraphList"]

        for item in items:
            content = item.get("content", "")
            if not content:
                continue

            # 关键词过滤
            if not any(kw in content for kw in FILTER_KEYWORDS):
                continue

            # 提取标题（取第一句或冒号前的内容，最多30字）
            title = _extract_title(content)

            score = score_text(title, content)

            # ctime 是 unix 时间戳
            ctime = item.get("ctime", 0)
            from datetime import datetime, timezone, timedelta
            bj_tz = timezone(timedelta(hours=8))
            if ctime and ctime > 1000000000:
                pub_time = datetime.fromtimestamp(ctime, tz=bj_tz).strftime("%Y-%m-%dT%H:%M:%S")
            else:
                pub_time = beijing_now()

            matched_stocks = [n for n in STOCK_NAMES if n in content]

            events.append({
                "title": title,
                "summary": content,
                "source": "cls",
                "source_url": item.get("shareurl", f"https://www.cls.cn/detail/{item.get('id','')}"),
                "published_at": pub_time,
                "stocks": [],
                "stock_names": matched_stocks,
                **score,
            })
    except Exception as e:
        print(f"[财联社] 抓取失败: {e}")

    return events


def _extract_title(content: str) -> str:
    """从电报正文提取标题"""
    content = content.strip()
    # 格式：【标题】正文... 或去掉【】里的内容后取前段
    if content.startswith("【"):
        end = content.find("】")
        if end > 1:
            tag = content[1:end]
            rest = content[end + 1:]
            if tag and len(tag) < 20:
                return tag
            return rest[:30] if len(rest) > 30 else rest
    return content[:30] if len(content) > 30 else content
