# 💰 billfusion · 零依赖账单合并分析仪

<!-- ORDER-CTA -->
> **需要定制或代做？** 我承接 Excel 代做（¥50 起）/ 零依赖 Python 脚本定制（¥200 起）/ 影刀·UiBot 机器人（¥500 起）。
> **先报价后付款、无预付款**，微信 / 支付宝结算，询价发 **2383844705@qq.com**（标题写「接单 + 需求类型」）。
> 更多工具与报价见作品集：https://zhiyilang.github.io/


把**微信支付 / 支付宝 / 银行卡**导出的 CSV 账单一键合并，自动**分类、去重、出月度报表**。

> 不用装任何东西，装了 Python 就能跑（Windows / macOS / Linux 通吃）。
> 你的账单**只在本机处理**，不上传任何服务器，隐私安全。

---

## ✨ 能干什么

- 🔗 **多平台合并**：微信、支付宝、银行卡的 CSV 一起丢进来，自动识别平台格式
- 🧹 **智能去重**：重复导出的账单自动剔除（按 时间+商户+金额+来源 判重）
- 🏷️ **自动分类**：餐饮 / 交通 / 购物 / 工资 / 转账 / 缴费 … 十余类关键词识别
- 📊 **月度报表**：每月收入、支出、结余一目了然
- 🏆 **Top 商户**：钱主要花在谁身上，一眼看清
- 📄 **双格式输出**：Markdown（可直接发好友/发朋友圈）+ HTML（浏览器打开好看）

---

## 🚀 三步上手

```bash
# 1. 从微信/支付宝导出账单 CSV（手机里「账单 → 导出」）
# 2. 把文件放一个文件夹，运行：
python main.py 微信账单.csv 支付宝账单.csv 银行卡.csv -o 报告.md

# 3. 想看网页版报表就加 --html：
python main.py *.csv --html 报告.html
```

就这么简单。**不需要 pip install，不需要联网，不需要注册。**

---

## 📋 输出示例

```
合并文件数: 2
原始交易笔数: 8 ｜ 去重后: 8 ｜ 重复剔除: 0
总入账: ¥16,059.90 ｜ 总支出: ¥355.40 ｜ 净结余: ¥15,704.50

## 月度收支
| 月份     | 收入       | 支出    | 结余        |
| 2026-10 | ¥16,059.90 | ¥355.40 | ¥15,704.50  |

## 支出分类
| 分类     | 支出    |
| 餐饮美食 | ¥63.50  |
| 购物消费 | ¥59.90  |
| 交通出行 | ¥32.00  |
```

---

## 🧩 支持的文件

| 平台 | 识别方式 | 备注 |
|------|----------|------|
| 微信支付 | 文件名含「微信」或内容含「微信支付账单」 | 自动跳过前导说明行 |
| 支付宝 | 文件名含「支付宝」或内容含「支付宝」 | 自动跳过前导说明行 |
| 银行卡 / 通用 | 其他 CSV（有 时间/金额/收支 列即可） | 列名自适应 |

> 微信/支付宝导出时选「用于个人对账」的 CSV 格式即可。

---

## 🛡️ 隐私说明

账单里全是你的消费记录，**本工具所有计算都在你本地完成**，不会上传任何数据。
如果你不放心，断网也能跑。

---

## 💝 赞助 / 支持

如果这个工具帮到了你，欢迎到 [爱发电](https://afdian.com/a/Zhiyilang) 请我喝杯咖啡 ☕
你的支持是我持续维护开源、做更多实用工具的动力。

MIT 开源协议，可自由商用、修改、分发。

<!-- cross-links -->

## 🔗 More zero-dependency tools

All of these are single-file, pure Python-stdlib CLIs — offline, no `pip install`, cross-platform:

- **lanshare** — LAN file transfer · <https://github.com/Zhiyilang/lanshare>
- **dupescan** — Duplicate file finder · <https://github.com/Zhiyilang/dupescan>
- **csvdiff** — CSV / JSON diff · <https://github.com/Zhiyilang/csvdiff>
- **md2html** — Markdown to HTML · <https://github.com/Zhiyilang/md2html>
- **dirsize** — Directory size analyzer · <https://github.com/Zhiyilang/dirsize>

Full portfolio & docs: <https://zhiyilang.github.io/>
