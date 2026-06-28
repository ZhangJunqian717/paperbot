# PaperBot — Daily AI Paper Email

每天自动推送一篇 Nature / 顶刊 AI 论文到你的邮箱。专为 AI 大二学生设计。

## How It Works

每天北京早上 8:00，GitHub Actions 自动运行：

1. **抓取** — 从 arXiv + Semantic Scholar 抓取最新 AI 论文
2. **打分** — 按以下规则排序：
   - 综述/Review 论文 +2 分
   - 引用 > 5000（里程碑论文）+3 分 / > 100 +2 分
   - 顶会/顶刊（NeurIPS, ICML, ICLR, CVPR, AAAI, Nature, Science 等）+1 分
   - 2024-2026 年论文 +3 分 / 2022-2023 年 +1 分
   - 2021 年前非里程碑论文自动过滤
3. **发送** — 最高分论文格式化 HTML 邮件发到你的邮箱

## 收到的邮件长这样

```
━━━━━━━━━━━━━━━━━━━━━━━━━
📄 Attention Is All You Need
━━━━━━━━━━━━━━━━━━━━━━━━━

📌 Source: NeurIPS 2017    📊 Citations: 120,000+

📝 Abstract: The dominant sequence transduction models are based on...

🔗 https://arxiv.org/abs/1706.03762

💡 Why this paper?
  → landmark paper — must-read in the field
━━━━━━━━━━━━━━━━━━━━━━━━━
📬 Delivered by PaperBot · Daily AI paper for students
```

## Setup

### 1. Fork 这个仓库

### 2. 获取 QQ 邮箱授权码

- 登录 QQ 邮箱 → 设置 → 账户
- 找到 **POP3/IMAP/SMTP 服务**，开启 **SMTP 服务**
- 按提示发送短信验证，会生成一个 **16 位授权码**，复制保存

### 3. 设置 GitHub Secrets

打开仓库 → Settings → Secrets and variables → Actions → New repository secret，添加 5 个：

| Secret | 值 |
|--------|-----|
| `SMTP_SERVER` | `smtp.qq.com` |
| `SMTP_PORT` | `587` |
| `SMTP_EMAIL` | `你的QQ号@qq.com` |
| `SMTP_PASSWORD` | 刚才的 QQ 邮箱授权码 |
| `RECIPIENT_EMAIL` | `接收推送的邮箱`（可以和上面一样） |

### 4. 手动测试

进入 Actions → Daily AI Paper → Run workflow → 手动触发，1-2 分钟后查收邮件。

### 5. 完事 🎉

每天早上 8 点自动推送，不用管它。

## 本地运行

```bash
cp .env.example .env
# 编辑 .env 填入真实邮箱和密码
pip install -r requirements.txt
python main.py
```

## License

MIT
