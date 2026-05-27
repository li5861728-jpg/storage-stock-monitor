import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "events.db")

# 存储板块相关股票池
WATCH_STOCKS = {
    "688981": "中芯国际",
    "688525": "佰维存储",
    "301308": "江波龙",
    "603986": "兆易创新",
    "300223": "北京君正",
    "688008": "澜起科技",
    "688256": "寒武纪",
    "002049": "紫光国微",
    "688385": "复旦微电",
    "688123": "聚辰股份",
    "300458": "全志科技",
    "688110": "东芯股份",
    "301269": "华大九天",
    "002185": "华天科技",
    "600584": "长电科技",
    "002156": "通富微电",
}

# 爬虫请求头
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

# 爬虫请求间隔（秒）
REQUEST_INTERVAL = 2

# 每页最大事件数
MAX_EVENTS_PER_PAGE = 200
