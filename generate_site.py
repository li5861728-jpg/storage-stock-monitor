#!/usr/bin/env python3
"""
运行所有爬虫 → 生成含数据的静态 HTML → 输出到 docs/index.html
GitHub Actions 定时运行此脚本，发布到 GitHub Pages
"""

import json
import sys
import os
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scraper.cls import fetch_telegraph
from scraper.eastmoney import fetch_sector_news, fetch_market_data
from scraper.jiwei import fetch_news
from analyzer.scorer import score_text

BJ_TZ = timezone(timedelta(hours=8))


def run_all():
    print(f"=== 开始抓取 {datetime.now(BJ_TZ).strftime('%Y-%m-%d %H:%M:%S')} 北京时间 ===")

    all_events = []
    scrapers = [
        ("财联社快讯", fetch_telegraph),
        ("东方财富公告", fetch_sector_news),
        ("东方财富行情", fetch_market_data),
        ("集微网行业", fetch_news),
    ]

    for name, fetcher in scrapers:
        try:
            events = fetcher()
            all_events.extend(events)
            print(f"  [{name}] {len(events)} 条")
        except Exception as e:
            print(f"  [{name}] 失败: {e}")
        time.sleep(0.5)

    # 去重 (source + source_url)
    seen = set()
    unique = []
    for e in all_events:
        key = (e["source"], e.get("source_url", ""))
        if key not in seen:
            seen.add(key)
            # 确保日期可JSON序列化
            e["published_at"] = str(e.get("published_at", ""))
            unique.append(e)
    unique.sort(key=lambda x: x.get("published_at", ""), reverse=True)

    print(f"  去重后: {len(unique)} 条")

    # 生成统计
    stats = _calc_stats(unique)

    # 按日分组
    grouped = {}
    for e in unique:
        day = e["published_at"][:10] if e["published_at"] else "unknown"
        if day not in grouped:
            grouped[day] = []
        grouped[day].append(e)

    gen_time = datetime.now(BJ_TZ).strftime("%Y-%m-%d %H:%M:%S")

    # 生成 HTML
    html = _build_html(unique, grouped, stats, gen_time)

    # 写入 docs/
    os.makedirs("docs", exist_ok=True)
    with open("docs/index.html", "w", encoding="utf-8") as f:
        f.write(html)

    print(f"  生成 docs/index.html ({len(html)} bytes)")
    print(f"=== 完成 {gen_time} ===")


def _calc_stats(events):
    total = len(events)
    bullish = sum(1 for e in events if e.get("sentiment") == "bullish")
    bearish = sum(1 for e in events if e.get("sentiment") == "bearish")
    neutral = total - bullish - bearish
    by_source = {}
    for e in events:
        s = e.get("source", "")
        by_source[s] = by_source.get(s, 0) + 1
    return {"total": total, "bullish": bullish, "bearish": bearish, "neutral": neutral, "by_source": by_source}


def _build_html(events, grouped, stats, gen_time):
    data_json = json.dumps({"events": events, "grouped": grouped, "stats": stats, "generated_at": gen_time}, ensure_ascii=False)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A股存储板块 · 信息时间线</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;background:#f5f5f7;color:#1d1d1f;line-height:1.6}}
a{{color:#2563eb;text-decoration:none}}a:hover{{text-decoration:underline}}
.app{{max-width:800px;margin:0 auto;padding:20px 16px 60px}}
.header{{text-align:center;padding:32px 0 20px;border-bottom:1px solid #e5e5e5;margin-bottom:20px}}
.header h1{{font-size:24px;font-weight:700;color:#111;letter-spacing:.5px}}
.subtitle{{font-size:13px;color:#86868b;margin-top:6px}}
.update-time{{font-size:12px;color:#a1a1a6;margin-top:4px}}
.toolbar{{background:#fff;border-radius:12px;padding:16px 20px;margin-bottom:20px;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.filter-row{{display:flex;gap:12px;align-items:flex-end;flex-wrap:wrap}}
.filter-group{{display:flex;flex-direction:column;gap:4px}}
.filter-group label{{font-size:12px;color:#86868b;font-weight:500}}
.filter-group select,.filter-group input{{padding:8px 12px;border:1px solid #d2d2d7;border-radius:8px;font-size:14px;outline:none;background:#fff;min-width:100px}}
.filter-group select:focus,.filter-group input:focus{{border-color:#2563eb;box-shadow:0 0 0 3px rgba(37,99,235,.1)}}
.btn{{padding:8px 20px;background:#2563eb;color:#fff;border:none;border-radius:8px;font-size:14px;cursor:pointer;font-weight:500}}
.btn:hover{{background:#1d4ed8}}
.stats-bar{{display:flex;gap:14px;margin-top:12px;padding-top:12px;border-top:1px solid #f0f0f0;flex-wrap:wrap;font-size:13px;color:#6e6e73}}
.stats-bar strong{{color:#1d1d1f}}.bullish strong{{color:#16a34a}}.bearish strong{{color:#dc2626}}
.timeline{{display:flex;flex-direction:column;gap:20px}}
.day-group{{background:#fff;border-radius:12px;overflow:hidden;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.day-header{{padding:14px 20px;background:#fafafa;border-bottom:1px solid #f0f0f0;display:flex;justify-content:space-between;align-items:center}}
.day-label{{font-weight:600;font-size:15px}}
.day-count{{font-size:12px;color:#86868b}}
.event-card{{padding:18px 20px;border-bottom:1px solid #f5f5f5;transition:background .15s}}
.event-card:last-child{{border-bottom:none}}
.event-card:hover{{background:#fafafa}}
.sentiment-bullish{{border-left:3px solid #16a34a}}
.sentiment-bearish{{border-left:3px solid #dc2626}}
.sentiment-neutral{{border-left:3px solid #d2d2d7}}
.event-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
.source-badge{{display:inline-block;padding:2px 8px;border-radius:4px;font-size:11px;color:#fff;font-weight:500}}
.event-time{{font-size:12px;color:#a1a1a6}}
.event-title{{font-size:16px;font-weight:600;margin-bottom:6px;line-height:1.4}}
.event-title a{{color:inherit}}.event-title a:hover{{color:#2563eb;text-decoration:none}}
.event-summary{{font-size:14px;color:#6e6e73;margin-bottom:12px;line-height:1.5}}
.sentiment-bar-container{{margin-bottom:10px}}
.sentiment-bar{{height:6px;border-radius:3px;overflow:hidden;display:flex;background:#f0f0f0}}
.bullish-fill{{background:#16a34a;height:100%}}
.bearish-fill{{background:#dc2626;height:100%}}
.sentiment-labels{{display:flex;justify-content:space-between;margin-top:4px;font-size:12px;font-weight:500}}
.bullish-label{{color:#16a34a}}.bearish-label{{color:#dc2626}}
.event-footer{{margin-top:4px}}
.event-tags{{display:flex;flex-wrap:wrap;gap:6px}}
.stock-tag{{display:inline-block;padding:2px 8px;background:#eff6ff;color:#1e40af;border-radius:4px;font-size:12px;font-weight:500}}
.kw-tag{{display:inline-block;padding:2px 8px;background:#f5f5f5;color:#6e6e73;border-radius:4px;font-size:11px}}
.footer{{text-align:center;padding:40px 0;color:#a1a1a6;font-size:12px}}
@media(max-width:600px){{.filter-row{{flex-direction:column}}.event-card{{padding:14px 16px}}.stats-bar{{gap:8px;font-size:12px}}}}
</style>
</head>
<body>
<div class="app">
<header class="header">
<h1>A股存储板块 · 信息时间线</h1>
<p class="subtitle">聚合财联社 / 东方财富 / 集微网 · 客观信息源</p>
<p class="update-time">更新时间：{gen_time} 北京时间 · 每30分钟自动刷新</p>
</header>
<div class="toolbar">
<div class="filter-row">
<div class="filter-group"><label>日期</label><select id="dateFilter"><option value="">全部日期</option></select></div>
<div class="filter-group"><label>情绪</label><select id="sentimentFilter"><option value="all">全部</option><option value="bullish">利好</option><option value="bearish">利空</option><option value="neutral">中性</option></select></div>
<div class="filter-group"><label>关键词</label><input type="text" id="keywordFilter" placeholder="搜索..."></div>
<button class="btn" id="searchBtn">筛选</button>
</div>
<div class="stats-bar">
<span>共 <strong id="statTotal">0</strong> 条</span>
<span class="bullish">利好 <strong id="statBullish">0</strong></span>
<span class="bearish">利空 <strong id="statBearish">0</strong></span>
<span>中性 <strong id="statNeutral">0</strong></span>
<span>财联社 <strong id="statCls">0</strong></span>
<span>东财 <strong id="statEm">0</strong></span>
<span>集微 <strong id="statJw">0</strong></span>
</div>
</div>
<main class="timeline" id="timeline"></main>
<footer class="footer">数据来源：财联社 东方财富 集微网 · 利好/利空评分基于关键词分析，仅供参考，不构成投资建议 · Powered by GitHub Pages</footer>
</div>
<script>
var DATA = {data_json};
var SOURCE_LABELS = {{cninfo:'巨潮资讯网',eastmoney:'东方财富',cls:'财联社',jiwei:'集微网'}};
var SOURCE_COLORS = {{cninfo:'#6366f1',eastmoney:'#f59e0b',cls:'#ef4444',jiwei:'#10b981'}};

(function(){{
var all=DATA.events,stats=DATA.stats;
document.title='A股存储板块 · 信息时间线 ('+stats.total+'条)';
document.getElementById('statTotal').textContent=stats.total;
document.getElementById('statBullish').textContent=stats.bullish;
document.getElementById('statBearish').textContent=stats.bearish;
document.getElementById('statNeutral').textContent=stats.neutral;
var by=stats.by_source||{{}};
document.getElementById('statCls').textContent=by.cls||0;
document.getElementById('statEm').textContent=(by.eastmoney||0);
document.getElementById('statJw').textContent=by.jiwei||0;

// 日期列表
var days=Object.keys(DATA.grouped).sort().reverse();
var sel=document.getElementById('dateFilter');
days.forEach(function(d){{var o=document.createElement('option');o.value=d;o.textContent=d;sel.appendChild(o);}});

// 渲染
renderTimeline();

document.getElementById('searchBtn').addEventListener('click',renderTimeline);
document.getElementById('keywordFilter').addEventListener('keydown',function(e){{if(e.key==='Enter')renderTimeline();}});

function renderTimeline(){{
var dateFilter=document.getElementById('dateFilter').value;
var sentFilter=document.getElementById('sentimentFilter').value;
var kw=document.getElementById('keywordFilter').value.toLowerCase();

var filtered=all.filter(function(e){{
if(dateFilter&&e.published_at.slice(0,10)!==dateFilter)return false;
if(sentFilter!=='all'&&e.sentiment!==sentFilter)return false;
if(kw&&(e.title+e.summary).toLowerCase().indexOf(kw)===-1)return false;
return true;
}});

var grouped={{}};
filtered.forEach(function(e){{
var day=e.published_at.slice(0,10)||'unknown';
if(!grouped[day])grouped[day]=[];
grouped[day].push(e);
}});
var fdays=Object.keys(grouped).sort().reverse();

var html='';
if(fdays.length===0){{html='<div style="text-align:center;padding:60px;color:#86868b">暂无匹配数据</div>';}}
else{{fdays.forEach(function(day){{
var events=grouped[day];
html+='<div class="day-group"><div class="day-header"><span class="day-label">'+day+'</span><span class="day-count">'+events.length+' 条</span></div><div class="day-items">';
events.forEach(function(e){{html+=renderEvent(e);}});
html+='</div></div>';
}});}}
document.getElementById('timeline').innerHTML=html;
}}

function renderEvent(e){{
var cls=e.sentiment==='bullish'?'sentiment-bullish':e.sentiment==='bearish'?'sentiment-bearish':'sentiment-neutral';
var time=e.published_at?e.published_at.slice(11,16):'--:--';
var stockTags=(e.stock_names||[]).map(function(n){{return'<span class="stock-tag">'+esc(n)+'</span>';}}).join('');
var kwTags=(e.keywords_matched||[]).slice(0,5).map(function(k){{return'<span class="kw-tag">'+esc(k)+'</span>';}}).join('');
var color=SOURCE_COLORS[e.source]||'#999';
var label=SOURCE_LABELS[e.source]||e.source;
var link=e.source_url?'<a href="'+esc(e.source_url)+'" target="_blank" rel="noopener">'+esc(e.title)+'</a>':esc(e.title);
var summary=(e.summary&&e.summary!==e.title)?'<p class="event-summary">'+esc(e.summary)+'</p>':'';
return'<div class="event-card '+cls+'"><div class="event-header"><span class="source-badge" style="background:'+color+'">'+label+'</span><span class="event-time">'+time+'</span></div><h3 class="event-title">'+link+'</h3>'+summary+'<div class="sentiment-bar-container"><div class="sentiment-bar"><div class="sentiment-fill bullish-fill" style="width:'+e.bullish_pct+'%"></div><div class="sentiment-fill bearish-fill" style="width:'+e.bearish_pct+'%"></div></div><div class="sentiment-labels"><span class="bullish-label">利好 '+e.bullish_pct+'%</span><span class="bearish-label">利空 '+e.bearish_pct+'%</span></div></div><div class="event-footer"><div class="event-tags">'+stockTags+kwTags+'</div></div></div>';
}}

function esc(s){{var d=document.createElement('div');d.textContent=s;return d.innerHTML;}}
}})();
</script>
</body>
</html>"""


def _git_push():
    """推送 docs/index.html 到 GitHub"""
    import subprocess
    import os
    proj_dir = os.path.dirname(os.path.abspath(__file__))
    try:
        subprocess.run(["git", "-C", proj_dir, "add", "docs/index.html"], check=True, capture_output=True)
        diff = subprocess.run(["git", "-C", proj_dir, "diff", "--staged", "--quiet"], capture_output=True)
        if diff.returncode == 0:
            print("  无变化，跳过推送")
            return
        subprocess.run(["git", "-C", proj_dir, "commit", "-m", f"auto update {gen_time()}"], check=True, capture_output=True)
        subprocess.run(["git", "-C", proj_dir, "push"], check=True, capture_output=True)
        print("  推送成功")
    except Exception as e:
        print(f"  推送失败: {e}")


def gen_time():
    from datetime import datetime, timezone, timedelta
    return datetime.now(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")


if __name__ == "__main__":
    run_all()
    _git_push()
