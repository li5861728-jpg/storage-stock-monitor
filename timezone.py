"""北京时间工具"""

from datetime import datetime, timezone, timedelta

BEIJING_TZ = timezone(timedelta(hours=8))


def beijing_now() -> str:
    """返回北京时间 ISO 8601 字符串"""
    return datetime.now(BEIJING_TZ).strftime("%Y-%m-%dT%H:%M:%S")


def to_beijing(dt_str: str) -> str:
    """将各种时间格式转为北京时间 ISO 8601"""
    if not dt_str:
        return beijing_now()

    dt_str = dt_str.strip()

    # 已经是 ISO 格式且带时区
    try:
        if "+" in dt_str:
            dt = datetime.fromisoformat(dt_str)
            return dt.astimezone(BEIJING_TZ).strftime("%Y-%m-%dT%H:%M:%S")
    except BaseException:
        pass

    # ISO 不带时区，假设备是北京时间
    try:
        if "T" in dt_str and len(dt_str) >= 16:
            dt = datetime.fromisoformat(dt_str.replace("Z", ""))
            return dt.strftime("%Y-%m-%dT%H:%M:%S")
    except BaseException:
        pass

    # "2025-01-15 10:30" 格式
    try:
        if " " in dt_str:
            dt_str_norm = dt_str.replace(" ", "T")
            datetime.fromisoformat(dt_str_norm)
            return dt_str_norm
    except BaseException:
        pass

    return dt_str
