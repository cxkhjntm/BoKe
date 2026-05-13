# BoKe -- 个人研究资料管理系统

[English](./README.md) | 中文

一款面向研究者的轻量级、安全的个人知识管理系统。支持文档上传与自动解析、全文搜索、LLM 对话集成、API Key 管理等功能，开箱即用。

## 功能特性

- **文档管理** -- 支持 PDF、DOCX、Markdown、图片等多种格式的上传、解析与管理
- **全文搜索** -- 基于 SQLite FTS5 引擎，快速检索文档内容
- **用户认证** -- JWT (HS256) 双令牌机制，支持 API Key (SHA256) 访问
- **文件处理** -- 自动提取文本、生成缩略图，后台异步处理
- **LLM 集成** -- 对接 OpenAI 兼容 API，支持可配置的大语言模型对话
- **RAG 检索增强** -- ChromaDB 向量存储 + langchain-text-splitters 文本分块
- **管理后台** -- 仪表盘统计、用户管理、系统监控
- **任务队列** -- Celery + Redis 异步任务处理（可选）
- **安全防护** -- 登录限流、CORS 配置、文件大小限制、输入校验
- **一键部署** -- 单脚本完成环境搭建、依赖安装、数据库迁移、前端构建

## 技术架构

```
+-----------------------------------------------------+
|                    Nginx (80)                        |
|   +------------+  +------------+  +----------------+ |
|   |   静态资源  |  |  /api/*    |  |  /storage/*    | |
|   |   (Vue3)   |  |  代理 ->   |  |  代理 ->       | |
|   +------------+  +-----+------+  +-------+--------+ |
|                         |                 |           |
+-------------------------+-----------------+-----------+
                          |                 |
                 +--------v-----------------v--------+
                 |      FastAPI 后端 (8000)           |
                 |  +------------+  +----------------+|
                 |  |   JWT      |  |   API Key      ||
                 |  |   认证     |  |   认证         ||
                 |  +------------+  +----------------+|
                 |  +------------+  +----------------+|
                 |  |  文档管理  |  |  处理流水线    ||
                 |  |  CRUD      |  |                ||
                 |  +------------+  +----------------+|
                 |  +------------+  +----------------+|
                 |  |  FTS5      |  |   文件存储     ||
                 |  |  全文搜索  |  |                ||
                 |  +------------+  +----------------+|
                 +-----------------+------------------+
                                   |
                 +-----------------v------------------+
                 |       SQLite + Alembic             |
                 |  (WAL 模式, 外键约束开启)          |
                 +------------------------------------+
```

## 技术栈

| 层级 | 技术 |
|------|------|
| 前端框架 | Vue 3, Vite, Pinia, Vue Router |
| 后端框架 | FastAPI, SQLAlchemy, Pydantic |
| 数据库 | SQLite (WAL 模式) |
| 数据库迁移 | Alembic |
| 认证方式 | JWT (HS256) + API Key (SHA256) |
| 文件处理 | PyMuPDF (PDF), python-docx (DOCX), Pillow (图片) |
| 任务队列 | Celery + Redis (可选) |
| 全文搜索 | SQLite FTS5 |
| LLM 集成 | OpenAI 兼容 API (可配置) |
| RAG | ChromaDB + langchain-text-splitters |

## 环境要求

| 依赖 | 版本 | 必填 | 说明 |
|------|------|------|------|
| Python | 3.11+ | 是 | 后端运行环境 |
| Node.js | 18+ | 是 | 前端构建 |
| Redis | 6.0+ | 否 | 可选，用于异步任务队列（Celery） |
| Nginx | 1.18+ | 否 | 生产环境推荐 |
| SQLite | 3.35+ | 是 | Python 自带，需支持 WAL 模式 |

**系统依赖（Linux）：**
- `build-essential`（Ubuntu）或 `gcc gcc-c++ make`（CentOS）
- `libmagic-dev`（Ubuntu）或 `file-devel`（CentOS），用于文件类型检测
- `curl`、`wget`、`git` 等基础工具

## 快速开始

### 前置要求

- Python 3.11+
- Node.js 18+ (用于前端构建)
- Redis (可选，用于 Celery 任务队列)

### 1. 克隆项目并配置

```bash
git clone https://github.com/cxkhjntm/BoKe.git
cd BoKe

# 从模板创建 .env 文件
cp .env.example .env

# 编辑 .env，至少设置以下两项：
#   JWT_SECRET_KEY=<openssl rand -hex 32>
#   ADMIN_PASSWORD=<你的密码>
```

### 2. 一键启动

```bash
bash run.sh
```

该脚本会自动完成以下操作：

- 创建 Python 虚拟环境
- 安装所有依赖
- 执行数据库迁移
- 构建 Vue3 前端
- 启动 FastAPI 服务

### 3. 访问系统

| 地址 | 说明 |
|------|------|
| http://localhost:8000 | Web 界面 |
| http://localhost:8000/docs | Swagger API 文档 |
| http://localhost:8000/api/v1/health | 健康检查 |

## 环境变量

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `JWT_SECRET_KEY` | 是 | -- | JWT 签名密钥（不少于 32 字符） |
| `ADMIN_PASSWORD` | 是 | -- | 管理员初始密码 |
| `ADMIN_USERNAME` | 否 | `admin` | 管理员用户名 |
| `DATABASE_URL` | 否 | `sqlite:///./data/app.db` | 数据库连接地址 |
| `STORAGE_PATH` | 否 | `./storage` | 文件存储根目录 |
| `MAX_UPLOAD_SIZE_MB` | 否 | `50` | 文档最大上传大小（MB） |
| `ALLOWED_EXTENSIONS` | 否 | `pdf,docx,md,png,jpg,jpeg` | 允许上传的文档扩展名 |
| `IMAGE_MAX_UPLOAD_SIZE_MB` | 否 | `2` | 图片最大上传大小（MB） |
| `IMAGE_ALLOWED_EXTENSIONS` | 否 | `png,jpg,jpeg,webp,gif` | 允许上传的图片扩展名 |
| `CORS_ORIGINS` | 否 | `http://localhost:5173` | 跨域允许来源 |
| `REDIS_URL` | 否 | `redis://localhost:6379/0` | Redis 连接地址 |
| `RATE_LIMIT_LOGIN` | 否 | `5` | 登录接口限流（次/分钟/IP） |
| `LOG_LEVEL` | 否 | `INFO` | 日志级别 |
| `REGISTRATION_ENABLED` | 否 | `false` | 是否开放注册 |
| `CHAT_MAX_TIMEOUT` | 否 | `120` | LLM 对话最大超时（秒） |
| `CHAT_MAX_MESSAGE_LENGTH` | 否 | `8000` | 对话消息最大长度（字符） |
| `CHAT_RATE_LIMIT_PER_MINUTE` | 否 | `20` | 对话接口限流（次/分钟） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 否 | `30` | 访问令牌有效期（分钟） |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 否 | `7` | 刷新令牌有效期（天） |

## API 参考

所有需要认证的接口支持两种方式：

- **JWT Bearer Token** -- 通过登录接口获取，放入 `Authorization: Bearer <token>` 请求头
- **API Key** -- 通过管理接口创建，放入 `Authorization: Bearer sk-<key>` 请求头

### 认证

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/auth/login` | 用户登录，返回访问令牌和刷新令牌 |
| POST | `/api/v1/auth/refresh` | 使用刷新令牌获取新的访问令牌 |
| POST | `/api/v1/auth/logout` | 登出，撤销刷新令牌 |

### 文档管理

| 方法 | 端点 | 说明 |
|------|------|------|
| POST | `/api/v1/documents` | 上传文档（multipart/form-data） |
| GET | `/api/v1/documents` | 获取文档列表（支持分页） |
| GET | `/api/v1/documents/{id}` | 获取单个文档详情 |
| PATCH | `/api/v1/documents/{id}` | 更新文档标题 |
| DELETE | `/api/v1/documents/{id}` | 删除文档及其关联文件 |
| POST | `/api/v1/documents/{id}/retry` | 重试失败的文档处理任务 |
| GET | `/api/v1/documents/search?q=` | 全文搜索文档内容 |

### 文件

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/files/{id}/original` | 下载原始文件 |
| GET | `/api/v1/files/{id}/thumbnail` | 获取文档缩略图 |

### API Key 管理

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/api-keys` | 获取 API Key 列表 |
| POST | `/api/v1/api-keys` | 创建新的 API Key |
| DELETE | `/api/v1/api-keys/{id}` | 删除指定 API Key |

### 系统与仪表盘

| 方法 | 端点 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查（无需认证） |
| GET | `/api/v1/dashboard/stats` | 获取系统统计数据 |
| GET | `/api/v1/dashboard/recent` | 获取最近上传的文档 |
| GET | `/api/v1/dashboard/top` | 获取热门文档排行 |

### 预留端点（尚未实现）

| 方法 | 端点 | 返回 |
|------|------|------|
| GET | `/api/v1/chat/` | `{"code": 5010, "message": "LLM integration is not available yet."}` |
| GET | `/api/v1/milvus/status` | `{"code": 0, "data": {"status": "not_configured"}}` |

## 项目结构

```
.
├── backend/
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 环境配置
│   ├── database.py          # SQLAlchemy 数据库设置
│   ├── celery_app.py        # Celery 任务队列配置
│   ├── tasks.py             # 异步任务定义
│   ├── models/              # ORM 数据模型
│   ├── schemas/             # Pydantic 数据模式
│   ├── routers/             # API 路由端点
│   ├── services/            # 业务逻辑层
│   ├── middleware/           # 中间件（认证、限流、日志）
│   ├── utils/               # 工具函数（JWT、日志、响应）
│   └── exceptions/          # 异常处理
├── frontend/
│   ├── src/
│   │   ├── api/             # Axios HTTP 客户端
│   │   ├── stores/          # Pinia 状态管理
│   │   ├── router/          # Vue Router 路由
│   │   ├── views/           # 页面组件
│   │   └── components/      # 公共组件
│   └── vite.config.js
├── alembic/                 # 数据库迁移脚本
├── tests/                   # 测试文件
├── docs/                    # 项目文档
├── nginx.conf               # Nginx 生产环境配置
├── requirements.txt         # Python 依赖清单
└── run.sh                   # 一键启动脚本
```

## 部署说明

### 开发环境

```bash
# 终端 1：启动后端
bash run.sh

# 终端 2：启动前端（支持热更新）
cd frontend && npm run dev
```

前端开发服务器默认运行在 http://localhost:5173，会自动代理 API 请求到后端 8000 端口。

### 生产环境部署

生产环境部署建议参考详细的部署手册：

📖 **[DEPLOYMENT.md](./DEPLOYMENT.md)** - 完整部署操作手册

部署手册涵盖以下内容：
- 服务器基础环境准备（Ubuntu/CentOS/Debian）
- Python 3.11+ 安装（源码编译）
- Node.js 18+ 安装
- Redis 安装与配置
- Nginx 反向代理配置
- Systemd 服务管理
- 防火墙配置
- SSL/HTTPS 配置（可选）

**快速生产部署：**

```bash
# 构建并启动
bash run.sh

# 配置 Nginx
sudo cp nginx.conf /etc/nginx/sites-available/boke
sudo ln -s /etc/nginx/sites-available/boke /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

生产环境下，Nginx 负责：

- 静态资源（Vue 构建产物）的直接服务
- `/api/*` 请求反向代理到 FastAPI 后端
- `/storage/*` 请求反向代理到文件服务
- HTTPS 终止（需自行配置证书）

## 更新说明

### 一键更新

项目提供了一键更新脚本：

```bash
cd ~/BoKe
chmod +x update.sh
bash update.sh
```

脚本会自动完成以下操作：
- 停止服务
- 备份数据库
- 拉取最新代码
- 更新 Python 依赖
- 运行数据库迁移
- 构建前端
- 重启服务
- 健康检查验证

### 手动更新

如果更新脚本执行失败或需要更精细的控制，请参考：

📖 **[UPDATE.md](./UPDATE.md)** - 详细更新指南

更新指南涵盖：
- 更新前准备与备份
- 手动更新详细步骤
- 版本间重大变更说明
- 更新后验证
- 回滚操作
- 常见问题排查

## 开发指南

### 运行测试

```bash
# 安装测试依赖（已包含在 requirements.txt 中）
pip install -r requirements.txt

# 执行全部测试
pytest

# 执行特定测试文件
pytest tests/test_documents.py

# 查看覆盖率
pytest --cov=backend --cov-report=term-missing
```

### 数据库迁移

```bash
# 生成新的迁移脚本
alembic revision --autogenerate -m "描述信息"

# 执行迁移
alembic upgrade head

# 回滚上一次迁移
alembic downgrade -1

# 查看当前版本
alembic current
```

## 许可证

MIT
