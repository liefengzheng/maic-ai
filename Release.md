# MAIC AI ECS 发布指南

本指南用于将 MAIC AI 发布到阿里云 ECS。生产环境通过 Docker Compose 运行 `api`、`web` 和 `nginx` 三个容器。

## 发布前准备

ECS 需要安装 Docker Engine 与 Docker Compose plugin：

```bash
docker --version
docker compose version
```

将项目克隆到 ECS，例如：

```bash
git clone <repository-url> /work/maic-ai
cd /work/maic-ai
```

生产环境的 API 配置位于 `apps/api/.env`。确认至少包含数据库、会话密钥和当前模型的 Azure 配置。该文件不应提交到 Git。

```dotenv
DATABASE_URL=postgresql://...
JWT_SECRET=...
AZURE_OPENAI_ENDPOINT=https://<resource>.openai.azure.com/
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_API_VERSION=2025-04-01-preview
AZURE_OPENAI_DEPLOYMENT=gpt-5.5
```

首次 API 启动时，如果 `llm_models` 表为空，系统会将这份 Azure 配置导入为默认模型；之后聊天时从数据库的模型目录读取配置。

## 从 uv 导出 requirements.txt

依赖的唯一来源仍是 `apps/api/pyproject.toml` 和 `apps/api/uv.lock`。当它们变更时，在开发机导出生产依赖：

```bash
cd apps/api
uv export --frozen --no-dev --no-hashes -o requirements.txt
```

提交 `requirements.txt` 以及 `pyproject.toml`、`uv.lock`：

```bash
git add apps/api/requirements.txt apps/api/pyproject.toml apps/api/uv.lock
git commit -m "Update API production dependencies"
git push
```

ECS 的 API Dockerfile 使用 `requirements.txt` 和阿里云 PyPI 镜像安装依赖，因此 ECS 不需要安装 uv。

```dockerfile
ENV PIP_INDEX_URL=https://mirrors.aliyun.com/pypi/simple/
COPY apps/api/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
```

如果阿里云镜像临时不可用，可在构建命令中覆盖为官方 PyPI：

```bash
docker compose build --build-arg PIP_INDEX_URL=https://pypi.org/simple api
```

当前 Dockerfile 使用环境变量而非 build argument；要使用官方源时，可临时删除或修改 Dockerfile 的 `PIP_INDEX_URL` 后重建。

## 常规发布

在 ECS 的项目根目录执行：

```bash
cd /work/maic-ai
git pull
docker compose build
docker compose run --rm api alembic upgrade head
docker compose up -d --force-recreate
docker compose ps
```

不要执行 `docker compose down -v`。`-v` 可能删除 Docker 管理的数据卷。普通代码发布不需要先执行 `docker compose down`；`up -d --force-recreate` 会使用新镜像替换已有容器。

仅更新 API 时：

```bash
docker compose build api
docker compose run --rm api alembic upgrade head
docker compose up -d --force-recreate api
```

仅更新 Web 时：

```bash
docker compose build web
docker compose up -d --force-recreate web
```

修改 `nginx/default.conf` 后，配置以 bind mount 方式挂载，只需重建 Nginx 容器：

```bash
docker compose up -d --force-recreate nginx
```

当前 Nginx 必须代理 `/models`，否则 Chat 页的模型选择器无法请求 `/models/available`。

## 验证与排障

查看服务状态：

```bash
docker compose ps
```

查看日志：

```bash
docker compose logs --tail=100 api
docker compose logs --tail=100 web
docker compose logs --tail=100 nginx
```

连续查看 API 日志：

```bash
docker compose logs -f api
```

检查迁移版本：

```bash
docker compose run --rm api alembic current
```

检查模型目录是否已初始化：

```bash
docker compose exec api python -c "import asyncio; from sqlalchemy import text; from app.database import get_engine; from sqlalchemy.ext.asyncio import async_sessionmaker; async def main():\n async with async_sessionmaker(get_engine())() as db: print((await db.execute(text('SELECT name, provider, model, enabled FROM llm_models'))).all())\nasyncio.run(main())"
```

预期至少有一条启用的 `gpt-5.5` / `azure_openai` 记录。若模型选择器为空，依次检查：

1. `llm_models` 是否有 `enabled = true` 的记录。
2. API 是否已重建并包含 `/models/available` 路由。
3. Nginx 配置的 API 路由正则是否包含 `models`。
4. 浏览器是否已强制刷新缓存。

## 国内网络构建缓慢

Docker Hub 可使用阿里云镜像加速器；专属地址在阿里云控制台的“容器镜像服务 ACR” -> “镜像工具” -> “镜像加速器”中获取。

`ghcr.io` 在中国大陆的访问可能很慢。当前 API Dockerfile 已不再依赖 `ghcr.io/astral-sh/uv`，改为使用 Docker Hub 的 Python 基础镜像和阿里云 PyPI 镜像。

如果 SSH 连接可能中断，请在 `tmux` 中构建：

```bash
tmux new -s maic-release
docker compose build
```

重新连接后恢复：

```bash
tmux attach -t maic-release
```
