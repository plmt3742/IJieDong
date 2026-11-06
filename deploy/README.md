# deploy · 部署

> 状态：占位（B-002/B-008 创建）。

## 职责

- 本地/演示环境的 Docker Compose。
- Nginx 反向代理（API/后台/H5）。
- 环境变量模板（不含真实密钥）。
- 部署、备份、回滚说明。

## 计划文件

```text
docker-compose.yml        # 演示/生产
docker-compose.dev.yml    # 本地依赖（PostgreSQL）
nginx.conf
.env.example
scripts/
README.md
```

## 环境

| 环境 | 用途 | 说明 |
|---|---|---|
| local | 开发 | Docker PostgreSQL + 本地进程 |
| demo | 演示 | 一台服务器 + HTTPS + 种子数据 |
| gov | 政务外网/粤政易 | 后期；SSO/私有化 LLM/国产库 |

## 边界

- 不提交 `.env`、证书私钥、数据库密码。
- 不把演示数据当真实数据。
- 生产变更必须有回滚步骤。
- 不承诺“已过等保/信创”；只记录准备状态。

## 下一步（B-002）

1. `docker-compose.dev.yml`：PostgreSQL。
2. `docker-compose.yml`：api + db + nginx。
3. `.env.example` + healthcheck。
4. README 写启动/备份/回滚。
