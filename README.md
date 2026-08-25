# MAIC AI

React + TypeScript + Vite 前端与 Node.js Fastify API 的 npm workspaces Monorepo。品牌、路由和页面文本均使用 `MAIC AI`。

## Start

1. 确认本机 PostgreSQL 已启动，并创建数据库 `maic_ai`。
2. 复制 `apps/api/.env.example` 为 `apps/api/.env`，填写本机 PostgreSQL 连接串并更新 `JWT_SECRET`；配置 Google 登录时填入 Google OAuth 凭据。
3. `python -m pip install -r apps/api/requirements.txt` 安装 Alembic。
4. `npm run db:migrate` 创建数据库表；该命令可重复执行，Alembic 会通过 `alembic_version` 跳过已执行的迁移。
5. `npm run dev` 启动 Web (`http://localhost:5173`) 与 API (`http://localhost:3001`)。

## Database

首个 PostgreSQL migration 位于 `apps/api/alembic/versions/001_initial_schema.py`，创建：

- `users`：邮箱密码帐户与公开资料。
- `oauth_accounts`：Google `sub` 与本地用户关联。
- `subscriptions`、`usage_ledger`：套餐和积分流水。
- `workshop_slots`、`workshop_bookings`：工作坊时段和预约。
- `conversations`、`chat_messages`：Chat 会话与 Markdown 内容。

Google 回调使用 `provider = google` 与不可变的 Google `sub` 查找账户；首次登录会创建用户，已有相同邮箱的本地账户会自动绑定。

后续迁移按 `002_功能描述.py`、`003_功能描述.py` 命名，且每个 migration 的 `down_revision` 指向前一个 revision。