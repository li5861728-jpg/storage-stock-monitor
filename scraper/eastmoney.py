"""东方财富 - 存储板块行情及公告新闻"""

import requests
from config import HEADERS
from analyzer.scorer import score_text
from timezone import beijing_now

WATCH_STOCK_CODES = [
    "603986", "301308", "688525", "300223", "688008",
    "688981", "002049", "688385", "688256", "688123",
    "688110", "600584", "002156", "002185", "300458",
]

STOCK_NAMES = {
    "603986": "兆易创新", "301308": "江波龙", "688525": "佰维存储",
    "300223": "北京君正", "688008": "澜起科技", "688981": "中芯国际",
    "002049": "紫光国微", "688385": "复旦微电", "688256": "寒武纪",
    "688123": "聚辰股份", "688110": "东芯股份", "600584": "长电科技",
    "002156": "通富微电", "002185": "华天科技", "300458": "全志科技",
}

IMPORTANT_COLUMNS = [
    "业绩", "预告", "合同", "中标", "增持", "减持", "回购",
    "收购", "重组", "定增", "配股", "停牌", "复牌", "分红",
    "研发", "专利", "政府补助", "诉讼", "仲裁",
    "产能", "投产", "封测", "芯片", "存储",
]


def fetch_sector_news() -> list[dict]:
    """抓取存储板块个股公告 + 板块行情"""
    events = []
    code_str = ",".join(WATCH_STOCK_CODES)

    try:
        url = (
            "https://np-anotice-stock.eastmoney.com/api/security/ann"
            f"?page_size=60&page_index=1&stock_list={code_str}"
        )
        resp = requests.get(
            url,
            headers={**HEADERS, "Referer": "https://www.eastmoney.com/"},
            timeout=15,
        )
        data = resp.json()
        items = data.get("data", {}).get("list", [])
    except Exception as e:
        print(f"[东方财富公告] 失败: {e}")
        return []

    for item in items:
        title = item.get("title", "")
        if not title:
            continue

        # 只保留重要公告
        if not _is_important(title):
            continue

        stock_code = item.get("stock_code", "")
        stock_name = STOCK_NAMES.get(stock_code, item.get("short_name", ""))

        score = score_text(title)

        display_time = item.get("display_time", "")
        if display_time:
            display_time = display_time[:19].replace(" ", "T")

        events.append({
            "title": title,
            "summary": f"{stock_name}({stock_code}) 公告",
            "source": "eastmoney",
            "source_url": item.get("url", ""),
            "published_at": display_time or beijing_now(),
            "stocks": [stock_code] if stock_code else [],
            "stock_names": [stock_name] if stock_name else [],
            **score,
        })

        if len(events) >= 30:
            break

    return events


def fetch_market_data() -> list[dict]:
    """抓取存储芯片概念板块行情"""
    try:
        url = (
            "https://push2.eastmoney.com/api/qt/clist/get?"
            "fid=f3&po=1&pz=10&pn=1&np=1&fltt=2&invt=2&"
            "fs=b:BK1139&fields=f2,f3,f4,f12,f14"
        )
        resp = requests.get(
            url,
            headers={**HEADERS, "Referer": "https://quote.eastmoney.com/"},
            timeout=15,
        )
        data = resp.json()
        items = data.get("data", {}).get("diff", []) if data.get("data") else []
        if not items:
            return []

        leading = items[:3]
        total_pct = sum(float(it.get("f3", 0)) for it in items) / len(items)

        if total_pct > 0.5:
            title = f"存储芯片板块上涨 {total_pct:.2f}%"
        elif total_pct < -0.5:
            title = f"存储芯片板块下跌 {abs(total_pct):.2f}%"
        else:
            title = f"存储芯片板块持平 ({total_pct:+.2f}%)"

        leaders = [f"{it.get('f14','')} {float(it.get('f3',0)):+.2f}%" for it in leading]
        summary = f"存储芯片概念板块涨跌幅 {total_pct:+.2f}%，领涨/跌: {', '.join(leaders)}"
        score = score_text(title, summary)

        return [{
            "title": title,
            "summary": summary,
            "source": "eastmoney",
            "source_url": "https://quote.eastmoney.com/bk/90.BK1139.html",
            "published_at": beijing_now(),
            "stocks": [it.get("f12", "") for it in items[:5]],
            "stock_names": [it.get("f14", "") for it in items[:5]],
            **score,
        }]
    except Exception as e:
        print(f"[东方财富行情] 失败: {e}")
        return []


def _is_important(title: str) -> bool:
    """判断公告是否重要"""
    title_lower = title.lower()
    return any(kw.lower() in title_lower for kw in IMPORTANT_COLUMNS)
