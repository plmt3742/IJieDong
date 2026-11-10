# deploy · 部署

> 状态：Demo v0 部署资产已建立；实际服务器部署待 AppID/域名/服务器确认。

## 职责

- 本地依赖（PostgreSQL）与演示/生产 Compose。
- Nginx 反向代理与静态后台。
- 环境变量模板（不含真实密钥）。
- 备份/恢复脚本与部署说明。

## 文件

```text
docker-compose.yml        # api + db + nginx
docker-compose.dev.yml    # 本地 PostgreSQL
nginx.conf
.env.example
scripts/backup.sh
scripts/restore.sh
```

## 本地开发

```bash
# 1. 启动本地 PostgreSQL
docker compose -f deploy/docker-compose.dev.yml --env-file deploy/.env up -d

# 2. 后端（SQLite Demo v0 可不用 PostgreSQL）
cd services/api
python -m alembic -c alembic.ini upgrade head
python scripts/seed_demo.py
python -m uvicorn app.main:app --reload

# 3. 后台
cd apps/admin
pnpm install
pnpm dev
```

## 演示/生产

```bash
cp deploy/.env.example deploy/.env
# 填写 POSTGRES_PASSWORD、JWT_SECRET、LLM_API_KEY、CORS_ORIGINS
pnpm install
VITE_API_BASE_URL=/api/v1 pnpm --filter @ijd/admin build
docker compose -f deploy/docker-compose.yml --env-file deploy/.env up -d --build
docker compose -f deploy/docker-compose.yml --env-file deploy/.env exec api \
  python -m alembic -c alembic.ini upgrade head
docker compose -f deploy/docker-compose.yml --env-file deploy/.env exec api \
  python scripts/seed_demo.py
docker compose -f deploy/docker-compose.yml --env-file deploy/.env exec api \
  python scripts/create_admin.py --username admin
```

访问 `http://<server>/`，API 在 `/api/v1`。TLS 由服务器现有 Nginx/Caddy 或云负载均衡终止；本项目 Nginx 只监听 80。

## 备份

```bash
cd deploy
./scripts/backup.sh
./scripts/restore.sh backups/ijiedong-YYYYmmdd-HHMMSS.sql.gz
```

备份默认保留 7 天；数据库卷为 `pgdata`。

## 环境

| 环境 | 用途 | 说明 |
|---|---|---|
| local | 开发 | 本地进程 + SQLite；可选 PostgreSQL |
| demo | 演示 | 一台服务器 + HTTPS + 种子数据 |
| gov | 政务外网/粤政易 | 后期；SSO/私有化 LLM/国产库 |

## 边界

- 不提交 `.env`、证书私钥、数据库密码。
- 不把演示数据当真实数据。
- 生产变更必须有回滚步骤。
- 不承诺“已过等保/信创”；只记录准备状态。
