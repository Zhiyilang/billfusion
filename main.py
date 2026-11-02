#!/usr/bin/env python3
# billfusion —— 零依赖账单合并分析仪
# 合并 微信支付 / 支付宝 / 银行卡 导出的 CSV 账单，自动分类、去重、出月度报表。
# 仅用 Python 标准库，任何装了 Python 的电脑都能跑（Windows / macOS / Linux）。
#
# 用法:
#   python main.py 微信账单.csv 支付宝账单.csv 银行卡.csv -o 报告.md
#   python main.py *.csv --html 报告.html
#   python main.py 账单.csv                      # 单文件也行
#
# 输出:
#   - Markdown 报表 (默认 报告.md)
#   - 可选 HTML 报表 (--html)
# 全部零依赖，不需要 pip install 任何东西。

import csv
import sys
import os
import re
import argparse
from collections import defaultdict
from datetime import datetime

# ---------- 分类关键词 ----------
CATEGORY_RULES = [
    ("工资薪水", ["工资", "薪资", "薪酬", "代发", "绩效", "奖金", "津贴"]),
    ("红包转账", ["红包", "转账", "零钱通", "理财", "退款", "退回"]),
    ("餐饮美食", ["餐饮", "饭店", "餐厅", "外卖", "美团", "饿了么", "咖啡", "奶茶", "小吃", "食堂", "肯德基", "麦当劳", "星巴克"]),
    ("交通出行", ["滴滴", "地铁", "公交", "打车", "加油", "停车", "高铁", "火车", "机票", "携程", "12306", "网约车"]),
    ("购物消费", ["淘宝", "天猫", "京东", "拼多多", "超市", "便利店", "唯品", "苏宁", "商城", "百货", "服饰", "数码"]),
    ("生活缴费", ["水费", "电费", "燃气", "物业", "宽带", "话费", "通信", "缴费", "供暖"]),
    ("医疗健康", ["医院", "药店", "诊所", "健康", "体检", "门诊", "卫生"]),
    ("娱乐休闲", ["电影", "视频", "会员", "游戏", "KTV", "健身", "旅游", "酒店", "门票", "网易云", "爱奇艺", "腾讯视频"]),
    ("教育学习", ["教育", "培训", "课程", "学校", "网课", "书籍", "图书", "知识"]),
    ("居家住宅", ["房租", "房东", "物业", "家居", "装修", "家政"]),
]

def categorize(counterparty: str, note: str, raw_category: str) -> str:
    text = f"{counterparty} {note} {raw_category}"
    for cat, kws in CATEGORY_RULES:
        for kw in kws:
            if kw in text:
                return cat
    return "其他"

# ---------- 各平台解析 ----------
def _norm_row(d: dict) -> dict:
    """把异构行归一成统一结构。"""
    date = d.get("_date", "")
    cp = d.get("_cp", "")
    note = d.get("_note", "")
    raw_cat = d.get("_cat", "")
    amount = d.get("_amount", 0.0)
    direction = d.get("_dir", "")  # 收入/支出
    # 方向判定
    if direction in ("支出", "借记", "付", "-"):
        sign = -1
    elif direction in ("收入", "贷记", "收", "+"):
        sign = 1
    else:
        sign = -1 if amount < 0 else 1
    amt = abs(amount) * sign
    month = ""
    m = re.search(r"(\d{4})[-/年.](\d{1,2})", date)
    if m:
        month = f"{int(m.group(1))}-{int(m.group(2)):02d}"
    return {
        "date": date.strip(),
        "month": month,
        "counterparty": cp.strip(),
        "note": note.strip(),
        "category": categorize(cp, note, raw_cat),
        "amount": round(amt, 2),
        "source": d.get("_source", ""),
    }

def parse_wechat(path: str):
    """微信支付账单: 前 ~16 行是说明，真正表头以 '交易时间' 开头。"""
    rows = []
    with open(path, encoding="utf-8-sig", errors="ignore") as f:
        lines = f.read().splitlines()
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("交易时间"):
            header_idx = i
            break
    if header_idx is None:
        return []
    reader = csv.DictReader(lines[header_idx:])
    for r in reader:
        rows.append(_norm_row({
            "_date": r.get("交易时间", ""),
            "_cp": r.get("交易对方", "") or r.get("商品", ""),
            "_note": r.get("商品", "") or r.get("交易对方", ""),
            "_cat": r.get("交易分类", "") or r.get("交易类型", ""),
            "_amount": _to_float(r.get("金额(元)", "")),
            "_dir": r.get("收/支", ""),
            "_source": "微信",
        }))
    return rows

def parse_alipay(path: str):
    """支付宝账单: 表头以 '交易时间' 开头，金额列 '金额', 方向 '收/支'。"""
    rows = []
    with open(path, encoding="utf-8-sig", errors="ignore") as f:
        lines = f.read().splitlines()
    header_idx = None
    for i, ln in enumerate(lines):
        if ln.startswith("交易时间"):
            header_idx = i
            break
    if header_idx is None:
        return []
    reader = csv.DictReader(lines[header_idx:])
    for r in reader:
        rows.append(_norm_row({
            "_date": r.get("交易时间", ""),
            "_cp": r.get("交易对方", "") or r.get("商品说明", ""),
            "_note": r.get("商品说明", "") or r.get("交易对方", ""),
            "_cat": r.get("交易分类", "") or r.get("交易类型", ""),
            "_amount": _to_float(r.get("金额", "")),
            "_dir": r.get("收/支", ""),
            "_source": "支付宝",
        }))
    return rows

def parse_generic(path: str):
    """通用 CSV: 尝试常见列名，失败则返回空。"""
    rows = []
    with open(path, encoding="utf-8-sig", errors="ignore") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return []
        fields = {k.lower(): k for k in reader.fieldnames}
        def g(*keys):
            for k in keys:
                if k in fields:
                    return fields[k]
            return None
        c_date = g("交易时间", "date", "时间", "datetime", "记账日期")
        c_cp = g("交易对方", "counterparty", "对方", "商户", "merchant", "name")
        c_note = g("商品说明", "note", "备注", "摘要", "desc", "memo")
        c_amt = g("金额", "amount", "金额(元)", "money", "交易金额")
        c_dir = g("收/支", "direction", "类型", "type", "收支")
        if not (c_date and c_amt):
            return []
        for r in reader:
            rows.append(_norm_row({
                "_date": r.get(c_date, ""),
                "_cp": r.get(c_cp, "") if c_cp else "",
                "_note": r.get(c_note, "") if c_note else "",
                "_cat": "",
                "_amount": _to_float(r.get(c_amt, "0")),
                "_dir": r.get(c_dir, "") if c_dir else "",
                "_source": "通用",
            }))
    return rows

def _to_float(s):
    if s is None:
        return 0.0
    s = str(s).replace(",", "").replace("¥", "").replace("$", "").strip()
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(s)
    except ValueError:
        return 0.0

def parse_file(path: str):
    name = os.path.basename(path).lower()
    if "微信" in name or "wechat" in name or "weixin" in name:
        rows = parse_wechat(path)
        if rows:
            return rows
    if "支付宝" in name or "alipay" in name:
        rows = parse_alipay(path)
        if rows:
            return rows
    # 内容探测
    try:
        with open(path, encoding="utf-8-sig", errors="ignore") as f:
            head = f.read(4000)
        if "微信支付账单" in head:
            return parse_wechat(path)
        if "支付宝" in head or "支付宝(中国)" in head:
            return parse_alipay(path)
    except Exception:
        pass
    return parse_generic(path)

# ---------- 报表 ----------
def build_report(rows):
    dedup = {}
    for r in rows:
        key = (r["date"], r["counterparty"], r["amount"], r["source"])
        if key not in dedup:
            dedup[key] = r
    clean = list(dedup.values())

    income = sum(r["amount"] for r in clean if r["amount"] > 0)
    expense = sum(-r["amount"] for r in clean if r["amount"] < 0)

    by_month = defaultdict(lambda: [0.0, 0.0])  # month -> [收入, 支出]
    by_cat = defaultdict(float)                 # cat -> 净支出(正数表示花出)
    by_source = defaultdict(lambda: [0.0, 0.0])
    top_merchants = defaultdict(float)          # 商户 -> 支出
    for r in clean:
        if r["month"]:
            if r["amount"] > 0:
                by_month[r["month"]][0] += r["amount"]
            else:
                by_month[r["month"]][1] += -r["amount"]
        if r["amount"] < 0:
            by_cat[r["category"]] += -r["amount"]
            top_merchants[r["counterparty"] or r["note"] or "未知"] += -r["amount"]
        else:
            by_source[r["source"]][0] += r["amount"]
        if r["amount"] < 0:
            by_source[r["source"]][1] += -r["amount"]

    return {
        "total": len(rows),
        "clean": len(clean),
        "dup": len(rows) - len(clean),
        "income": income,
        "expense": expense,
        "by_month": dict(sorted(by_month.items())),
        "by_cat": dict(sorted(by_cat.items(), key=lambda x: -x[1])),
        "by_source": dict(by_source),
        "top_merchants": dict(sorted(top_merchants.items(), key=lambda x: -x[1])[:10]),
    }

def render_md(rep, files):
    L = []
    L.append("# 💰 账单合并分析报告\n")
    L.append(f"- 合并文件数: **{len(files)}**")
    L.append(f"- 原始交易笔数: **{rep['total']}** ｜ 去重后: **{rep['clean']}** ｜ 重复剔除: **{rep['dup']}**")
    L.append(f"- 总入账: **¥{rep['income']:,.2f}** ｜ 总支出: **¥{rep['expense']:,.2f}** ｜ 净结余: **¥{rep['income']-rep['expense']:,.2f}**\n")
    L.append("## 月度收支\n")
    L.append("| 月份 | 收入 | 支出 | 结余 |")
    L.append("|------|------|------|------|")
    for m, (inc, exp) in rep["by_month"].items():
        L.append(f"| {m} | ¥{inc:,.2f} | ¥{exp:,.2f} | ¥{inc-exp:,.2f} |")
    L.append("\n## 支出分类\n")
    L.append("| 分类 | 支出 |")
    L.append("|------|------|")
    for c, v in rep["by_cat"].items():
        L.append(f"| {c} | ¥{v:,.2f} |")
    L.append("\n## 支出 Top 商户\n")
    L.append("| 商户 | 支出 |")
    L.append("|------|------|")
    for m, v in rep["top_merchants"].items():
        L.append(f"| {m} | ¥{v:,.2f} |")
    L.append("\n## 按来源\n")
    L.append("| 来源 | 收入 | 支出 |")
    L.append("|------|------|------|")
    for s, (inc, exp) in rep["by_source"].items():
        L.append(f"| {s} | ¥{inc:,.2f} | ¥{exp:,.2f} |")
    L.append("\n---\n_本报告由 [billfusion](https://github.com/Zhiyilang/billfusion) 零依赖生成。如果这个工具帮到你，欢迎到 [爱发电](https://afdian.com/a/Zhiyilang) 请作者喝杯咖啡 ☕_")
    return "\n".join(L)

def render_html(rep):
    rows_month = "".join(
        f"<tr><td>{m}</td><td>¥{inc:,.2f}</td><td>¥{exp:,.2f}</td><td>¥{inc-exp:,.2f}</td></tr>"
        for m, (inc, exp) in rep["by_month"].items())
    rows_cat = "".join(f"<tr><td>{c}</td><td>¥{v:,.2f}</td></tr>" for c, v in rep["by_cat"].items())
    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<title>账单合并分析报告</title><style>
body{{font-family:-apple-system,Segoe UI,Roboto,'Microsoft YaHei',sans-serif;max-width:760px;margin:40px auto;padding:0 16px;color:#222}}
h1{{font-size:22px}} table{{border-collapse:collapse;width:100%;margin:10px 0 24px}} th,td{{border:1px solid #e3e3e3;padding:8px 10px;text-align:left}} th{{background:#f6f6f6}}
.kpi{{display:flex;gap:16px;flex-wrap:wrap;margin:16px 0}} .kpi div{{background:#fafafa;border:1px solid #eee;border-radius:10px;padding:12px 16px}} .kpi b{{font-size:18px;display:block}}
</style></head><body>
<h1>💰 账单合并分析报告</h1>
<div class="kpi">
<div>原始笔数<b>{rep['total']}</b></div>
<div>去重后<b>{rep['clean']}</b></div>
<div>重复剔除<b>{rep['dup']}</b></div>
<div>总入账<b>¥{rep['income']:,.2f}</b></div>
<div>总支出<b>¥{rep['expense']:,.2f}</b></div>
<div>净结余<b>¥{rep['income']-rep['expense']:,.2f}</b></div>
</div>
<h2>月度收支</h2><table><tr><th>月份</th><th>收入</th><th>支出</th><th>结余</th></tr>{rows_month}</table>
<h2>支出分类</h2><table><tr><th>分类</th><th>支出</th></tr>{rows_cat}</table>
<p style="color:#888;font-size:13px">由 billfusion 零依赖生成 · <a href="https://afdian.com/a/Zhiyilang">爱发电赞助</a></p>
</body></html>"""

def main():
    ap = argparse.ArgumentParser(description="零依赖账单合并分析仪")
    ap.add_argument("files", nargs="+", help="一个或多个 CSV 账单文件")
    ap.add_argument("-o", "--output", default="报告.md", help="Markdown 输出路径")
    ap.add_argument("--html", help="额外输出 HTML 报表路径")
    args = ap.parse_args()

    all_rows = []
    for fp in args.files:
        if not os.path.exists(fp):
            print(f"[跳过] 文件不存在: {fp}", file=sys.stderr)
            continue
        rows = parse_file(fp)
        print(f"[读取] {fp}: {len(rows)} 行")
        all_rows.extend(rows)

    if not all_rows:
        print("没有解析到任何交易记录。请确认是微信/支付宝/银行卡导出的 CSV。", file=sys.stderr)
        sys.exit(1)

    rep = build_report(all_rows)
    md = render_md(rep, args.files)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"[写出] {args.output} (去重后 {rep['clean']} 笔, 支出 ¥{rep['expense']:,.2f})")
    if args.html:
        with open(args.html, "w", encoding="utf-8") as f:
            f.write(render_html(rep))
        print(f"[写出] {args.html}")

if __name__ == "__main__":
    main()
