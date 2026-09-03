# MAIC AI

React + TypeScript + Vite 前端与 Python 3.12 FastAPI API 的 npm workspaces Monorepo。AI 编排使用 LangChain Deep Agents，并通过 LLM Adapter 支持多个模型供应商；API 继续监听 `3001`。

## Start

1. 确认本机 PostgreSQL 已启动，并创建数据库 `maic_ai`。
2. 安装 Python 3.12 与 [uv](https://docs.astral.sh/uv/)，运行 `uv sync --project apps/api`。依赖由 `apps/api/pyproject.toml` 与 `apps/api/uv.lock` 管理。
3. 复制 `apps/api/.env.example` 为 `apps/api/.env`，填写 PostgreSQL、`JWT_SECRET` 与下方 LLM 配置；配置 Google 登录时再填入 Google OAuth 凭据。
4. `npm run db:migrate` 创建数据库表；该命令可重复执行，Alembic 会通过 `alembic_version` 跳过已执行的迁移。
5. `npm run dev` 启动 Web (`http://localhost:5173`) 与 API (`http://localhost:3001`)。

## Agent

- `coordinator`：未选择目录 Agent 时使用的基础 Agent。
- 目录 Agent：由 system prompt 和关联 Skills 动态构建。

用户分为 `admin` 与 `user`。只有 `admin` 可以管理全局 Skill、Agent、SuperAgent 和生成 Graph；所有用户都可以使用全局目录中已启用的 Agent。管理员通过 `POST /agents` 保存 Agent 定义，再通过 `POST /agents/{id}/graph` 验证并生成运行 Graph。

Graph 不序列化到数据库。API 根据 Agent 的 system prompt 与 Skill 关系按需编译 Deep Agents Graph；SuperAgent 则把有序成员 Agent 编译为 subagents。Chat 会缓存已编译 Graph，并在 Agent 的 `updated_at` 改变后生成新版本。

API 启动时会读取所有已启用的 Agent 与 SuperAgent，根据其 Skill 关联动态生成并缓存 Graph。Skill 元数据保存在数据库中，执行逻辑从 `apps/api/app/runtime/skills/<handler>/skill.py` 动态加载；单个 Graph 构建失败会记录日志但不会阻止其他 Agent 和 API 启动，每个 Graph 最多等待 30 秒。

聊天使用 `POST /conversations/{id}/runs` 返回 SSE。事件包括 `token`、`skill`、`done` 和 `error`。普通认证、预约和数据库写入仍由确定性的 FastAPI 服务处理，不交给模型。

## LLM Adapter

通过 `LLM_PROVIDER` 切换模型：`openai`、`azure_openai`、`anthropic`、`deepseek`、`kimi`、`minimax`、`gemini` 或 `openai_compatible`。

- `azure_openai` 使用 `AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_API_KEY`、`AZURE_OPENAI_API_VERSION` 和 `AZURE_OPENAI_DEPLOYMENT`。
- `openai`、`anthropic`、`gemini` 使用 `LLM_MODEL` 和 `LLM_API_KEY`；`LLM_BASE_URL` 可选。
- `deepseek`、`kimi`、`minimax` 使用 `LLM_MODEL` 和 `LLM_API_KEY`，默认连接各自的 OpenAI-compatible 地址，也可通过 `LLM_BASE_URL` 覆盖。
- 其他 OpenAI-compatible 服务使用 `LLM_PROVIDER=openai_compatible`，并显式设置 `LLM_BASE_URL`。

修改 LLM 配置后需要重启 API，因为 Agent 会在首次请求时创建并缓存。

新增供应商时，在 `apps/api/app/llm/providers` 中添加一个文件，将该供应商的 Settings class 与 `LlmAdapter` 子类放在一起。设置 `provider_names` 并实现 `create()` 后，工厂会自动发现并注册，无需修改 Agent、中央配置或供应商列表。

## Database

首个 PostgreSQL migration 位于 `apps/api/alembic/versions/001_initial_schema.py`，创建：

- `users`：邮箱密码帐户、公开资料与 `admin`/`user` 角色。
- `oauth_accounts`：Google `sub` 与本地用户关联。
- `subscriptions`、`usage_ledger`：套餐和积分流水。
- `workshop_slots`、`workshop_bookings`：工作坊时段和预约。
- `conversations`、`chat_messages`：Chat 会话与 Markdown 内容。
- `agents`：管理员设计的全局 Agent，通过 `owner_user_id` 记录创建者。
- `skill_registry`：全局 Skill 元数据、输入输出 Schema 与执行配置。
- `agent_skills`：Agent 与 Skill 的多对多关系。
- `super_agents`、`super_agent_members`：全局 SuperAgent 及其有序的单独 Agent 成员，不能嵌套 SuperAgent。

Google 回调使用 `provider = google` 与不可变的 Google `sub` 查找账户；首次登录会创建用户，已有相同邮箱的本地账户会自动绑定。

后续迁移按 `002_功能描述.py`、`003_功能描述.py` 命名，且每个 migration 的 `down_revision` 指向前一个 revision。

Alembic 通过 `alembic_version` 保证 `npm run db:migrate` 可重复执行；PostgreSQL 使用事务型 DDL，迁移失败会整体回滚。不要用 `IF NOT EXISTS` 跳过结构冲突，否则会掩盖数据库与 migration 历史不一致的问题。
