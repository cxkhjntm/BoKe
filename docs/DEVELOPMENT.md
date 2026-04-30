# 技术规范文档 - 个人研究资料管理系统

## 1. 技术栈

| 层 | 技术选型 | 版本约束 |
|---|---|---|
| Web 框架 | FastAPI | >=0.100,<1.0 |
| ORM | SQLAlchemy | >=2.0,<3.0 |
| 数据库 | SQLite | 3.x (内置) |
| 迁移 | Alembic | >=1.12,<2.0 |
| 认证 | PyJWT + pwdlib[bcrypt] | >=2.8,<3.0 + >=0.3,<1.0 |
| 文件处理 | python-multipart, Pillow, PyMuPDF, python-docx, python-magic | Pillow>=10.0,<11.0; PyMuPDF>=1.23,<2.0; python-docx>=1.0,<2.0; python-magic>=0.4,<1.0 |
| 前端 | Vue3 + Vite | 3.x |
| 反向代理 | Nginx | 1.24+ |

## 2. 项目目录结构

```
BoKe/
├── README.md
├── docs/
│   └── DEVELOPMENT.md          # 本文档
├── requirements.txt
├── run.sh
├── nginx.conf
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 001_initial.py
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app 入口
│   ├── config.py                # 配置（环境变量读取）
│   ├── database.py              # 数据库连接
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py              # 用户模型
│   │   ├── document.py          # 文档模型
│   │   └── api_key.py           # API Key 模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py            # 统一返回结构
│   │   ├── user.py
│   │   ├── document.py
│   │   └── api_key.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py              # 登录 / 刷新 Token
│   │   ├── documents.py         # 文档 CRUD
│   │   ├── search.py            # 搜索接口
│   │   ├── files.py             # 文件访问（鉴权后返回文件）
│   │   ├── chat.py              # LLM 预留
│   │   ├── milvus.py            # Milvus 预留
│   │   ├── api_keys.py          # API Key 管理
│   │   ├── admin.py             # 管理接口（FTS 重建等）
│   │   └── health.py            # 健康检查
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth_service.py      # 认证逻辑
│   │   ├── document_service.py  # 文档业务逻辑
│   │   ├── file_service.py      # 文件存储操作
│   │   ├── extract_service.py   # 文本提取（PDF/DOCX/MD）
│   │   ├── thumbnail_service.py # 缩略图生成（全类型）
│   │   └── processing_service.py # 文档处理管线（文本提取+缩略图编排）
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py              # JWT 中间件
│   │   └── rate_limit.py        # 限流中间件
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── response.py          # 统一响应工具
│   │   ├── security.py          # 密码哈希、JWT 工具
│   │   └── logger.py            # 日志配置
│   └── exceptions/
│       ├── __init__.py
│       └── handlers.py          # 统一异常处理
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── router/
│   │   │   └── index.js
│   │   ├── stores/
│   │   │   └── auth.js
│   │   ├── api/
│   │   │   └── index.js         # axios 封装
│   │   ├── views/
│   │   │   ├── Login.vue
│   │   │   ├── Upload.vue
│   │   │   ├── Documents.vue
│   │   │   └── Reader.vue
│   │   └── components/
│   │       ├── Navbar.vue
│   │       └── SearchBar.vue
│   └── public/
└── storage/                     # 运行时生成，不入 Git
    └── {user_id}/
        ├── original/
        ├── processed/
        └── thumbnails/
```

## 3. 环境变量清单

| 变量名 | 用途 | 示例值 | 默认值 |
|---|---|---|---|
| DATABASE_URL | SQLite 数据库路径 | sqlite:///./data/app.db | sqlite:///./data/app.db |
| JWT_SECRET_KEY | JWT 签名密钥 (openssl rand -hex 32 生成) | (随机64位十六进制字符串) | (无，必须设置，>=32字节) |
| JWT_ALGORITHM | JWT 算法 | HS256 | HS256 |
| ACCESS_TOKEN_EXPIRE_MINUTES | Access Token 过期时间(分钟) | 30 | 30 |
| REFRESH_TOKEN_EXPIRE_DAYS | Refresh Token 过期时间(天) | 7 | 7 |
| ADMIN_USERNAME | 初始管理员用户名 | admin | admin |
| ADMIN_PASSWORD | 初始管理员密码 (生产环境用 secrets manager) | (无) | (无，必须设置) |
| STORAGE_PATH | 文件存储根路径 | ./storage | ./storage |
| MAX_UPLOAD_SIZE_MB | 最大上传文件大小(MB) | 50 | 50 |
| ALLOWED_EXTENSIONS | 允许的文件扩展名 | pdf,docx,md,png,jpg,jpeg | pdf,docx,md,png,jpg,jpeg |
| LOG_LEVEL | 日志级别 | INFO | INFO |
| CORS_ORIGINS | 允许的跨域来源 | http://localhost:5173 | http://localhost:5173 |
| RATE_LIMIT_LOGIN | 登录限流(次/分钟/IP) | 5 | 5 |
| REGISTRATION_ENABLED | 是否开放注册 | false | false |

## 4. 数据库 Schema

### 4.1 users 表

```sql
CREATE TABLE users (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    username            VARCHAR(50) UNIQUE NOT NULL,
    password_hash       VARCHAR(128) NOT NULL,
    is_admin            BOOLEAN DEFAULT FALSE,
    is_active           BOOLEAN DEFAULT TRUE,
    login_failures      INTEGER DEFAULT 0,
    locked_until        DATETIME,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4.2 documents 表

```sql
CREATE TABLE documents (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id         INTEGER NOT NULL REFERENCES users(id),
    title           VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type       VARCHAR(20) NOT NULL,        -- pdf, docx, md, png, jpg, jpeg
    file_size       INTEGER NOT NULL,             -- 字节
    file_path       VARCHAR(500) NOT NULL,        -- 存储路径 (相对于 STORAGE_PATH)
    thumbnail_path  VARCHAR(500),                 -- 缩略图路径
    content_text    TEXT,                          -- 提取的文本内容
    status          VARCHAR(20) DEFAULT 'processing', -- queued / processing / ready / error
    error_message   TEXT,                          -- 处理失败时的错误信息（脱敏）
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    CHECK (file_type IN ('pdf','docx','md','png','jpg','jpeg')),
    CHECK (status IN ('queued','processing','ready','error'))
);

CREATE INDEX idx_documents_user_id ON documents(user_id);
CREATE INDEX idx_documents_status ON documents(status);
```

### 4.2.1 文档状态机

```
         [Upload/Create]
              │
              ▼
           queued ──────→ (Stage C: 异步模式)
              │
              ▼
          processing ──→ (当前: 同步模式，立即执行)
           /      \
          ▼        ▼
       ready     error
                  │
                  ▼ (retry)
              processing
```

| 状态 | 含义 | 前端展示 | 可删除 | 可重试 |
|------|------|---------|--------|--------|
| `queued` | 已入队，等待处理 | 蓝色标签 "Queued" | 否 | 否 |
| `processing` | 正在处理中 | 黄色标签 "Processing" | 否 | 否 |
| `ready` | 处理完成 | 绿色标签 "Ready" | 是 | 否 |
| `error` | 处理失败 | 红色标签 "Error" + 错误信息 | 是 | 是 |

数据库层通过 CHECK 约束强制状态合法性：`CHECK (status IN ('queued','processing','ready','error'))`

### 4.3 documents_fts 表 (FTS5 虚拟表)

```sql
CREATE VIRTUAL TABLE documents_fts USING fts5(
    title,
    content_text,
    content='documents',
    content_rowid='id'
);

-- 触发器保持同步
CREATE TRIGGER documents_ai AFTER INSERT ON documents BEGIN
    INSERT INTO documents_fts(rowid, title, content_text)
    VALUES (new.id, new.title, new.content_text);
END;

CREATE TRIGGER documents_ad AFTER DELETE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, content_text)
    VALUES ('delete', old.id, old.title, old.content_text);
END;

CREATE TRIGGER documents_au AFTER UPDATE ON documents BEGIN
    INSERT INTO documents_fts(documents_fts, rowid, title, content_text)
    VALUES ('delete', old.id, old.title, old.content_text);
    INSERT INTO documents_fts(rowid, title, content_text)
    VALUES (new.id, new.title, new.content_text);
END;
```

### 4.4 api_keys 表

```sql
CREATE TABLE api_keys (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    name        VARCHAR(100) NOT NULL,
    key_hash    VARCHAR(128) NOT NULL,            -- SHA256 哈希（API Key 为高熵随机值，无需慢哈希）
    key_prefix  VARCHAR(8) NOT NULL,              -- 前缀用于展示 (如 "sk-xxxx")
    is_active   BOOLEAN DEFAULT TRUE,
    last_used_at DATETIME,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at  DATETIME
);

CREATE INDEX idx_api_keys_user_id ON api_keys(user_id);
```

### 4.5 refresh_tokens 表

```sql
CREATE TABLE refresh_tokens (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    jti         VARCHAR(36) UNIQUE NOT NULL,       -- JWT ID (UUID)，用于精确匹配和撤销
    expires_at  DATETIME NOT NULL,
    revoked     BOOLEAN DEFAULT FALSE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_jti ON refresh_tokens(jti);
```

## 5. API 规范

### 5.1 统一返回结构

成功:
```json
{ "code": 0, "message": "ok", "data": { ... } }
```

错误:
```json
{ "code": 4001, "message": "Invalid token", "data": null }
```

错误码定义:
| 错误码 | 含义 |
|---|---|
| 0 | 成功 |
| 4000 | 请求参数错误 |
| 4001 | Token 无效或过期 |
| 4003 | 权限不足 |
| 4004 | 资源不存在 |
| 4005 | 操作冲突（如文档处理中尝试删除） |
| 4009 | 文件类型不允许 |
| 4010 | 文件过大 |
| 4011 | 文件内容校验失败 |
| 4029 | 请求过于频繁 |
| 4030 | 账户已锁定 |
| 5000 | 服务器内部错误 |
| 5010 | 功能尚未开放（预留接口） |

### 5.2 API 端点列表

#### 认证

```
POST /api/v1/auth/login
  Body: { "username": "admin", "password": "xxx" }
  Response: { "code": 0, "message": "ok", "data": { "access_token": "...", "refresh_token": "...", "token_type": "bearer" } }

POST /api/v1/auth/refresh
  Body: { "refresh_token": "..." }
  Response: { "code": 0, "message": "ok", "data": { "access_token": "...", "refresh_token": "...", "token_type": "bearer" } }

POST /api/v1/auth/logout
  Header: Authorization: Bearer <access_token>
  Body: { "refresh_token": "..." }
  Response: { "code": 0, "message": "ok", "data": null }
```

#### 文档

```
POST /api/v1/documents
  Header: Authorization: Bearer <access_token>
  Body: multipart/form-data { file: <binary>, title: "可选标题" }
  注: 单文件上传，进度由浏览器 XMLHttpRequest.upload.onprogress 获取
  Response:
  {
    "code": 0, "message": "ok",
    "data": {
      "id": 1, "title": "文档标题", "original_filename": "原始文件名.pdf",
      "file_type": "pdf", "file_size": 1024000, "status": "processing",
      "error_message": null, "created_at": "2026-04-29T10:00:00", "updated_at": "2026-04-29T10:00:00"
    }
  }

GET /api/v1/documents
  Header: Authorization: Bearer <access_token>
  Query: page=1&limit=20&sort_by=created_at&sort_order=desc&status=ready&file_type=pdf
    - sort_by: created_at | file_size | title (默认 created_at)
    - sort_order: asc | desc (默认 desc)
    - status: queued | processing | ready | error (可选筛选)
    - file_type: pdf | docx | md | png | jpg | jpeg (可选筛选)
    - limit: 最大 100
  Response:
  {
    "code": 0, "message": "ok",
    "data": {
      "items": [
        {
          "id": 1, "title": "文档标题", "original_filename": "原始文件名.pdf",
          "file_type": "pdf", "file_size": 1024000, "thumbnail_path": null,
          "status": "ready", "error_message": null,
          "created_at": "2026-04-29T10:00:00", "updated_at": "2026-04-29T10:00:00"
        }
      ],
      "total": 100, "page": 1, "limit": 20
    }
  }

GET /api/v1/documents/{id}
  Header: Authorization: Bearer <access_token>
  Response:
  {
    "code": 0, "message": "ok",
    "data": {
      "id": 1, "title": "文档标题", "original_filename": "原始文件名.pdf",
      "file_type": "pdf", "file_size": 1024000, "file_path": "1/original/uuid.pdf",
      "thumbnail_path": "1/thumbnails/uuid_thumb.jpg", "content_text": "提取的文本...",
      "status": "ready", "error_message": null,
      "created_at": "2026-04-29T10:00:00", "updated_at": "2026-04-29T10:05:00"
    }
  }

DELETE /api/v1/documents/{id}
  Header: Authorization: Bearer <access_token>
  注: 文档处理中(status=queued/processing)时不允许删除，返回 4005
  Response: { "code": 0, "message": "ok", "data": null }

POST /api/v1/documents/{id}/retry
  Header: Authorization: Bearer <access_token>
  注: 仅 status=error 的文档可重试，返回 4009 其他状态
  Response:
  {
    "code": 0, "message": "ok",
    "data": {
      "id": 1, "title": "文档标题", "status": "processing",
      "error_message": null, ...
    }
  }
```

#### 搜索

```
GET /api/v1/documents/search?q=keyword
  Header: Authorization: Bearer <access_token>
  Query: q=keyword&page=1&limit=20
  注: 搜索关键词自动进行 FTS5 安全处理（去除控制字符, 双引号转义, 短语搜索模式）
      禁止直接传入 FTS5 运算符 (AND/OR/NOT/NEAR/*/-)
  Response:
  {
    "code": 0, "message": "ok",
    "data": {
      "items": [
        {
          "id": 1, "title": "文档标题", "file_type": "pdf", "status": "ready",
          "snippet": "...匹配上下文文本（前后各100字符）...",
          "created_at": "2026-04-29T10:00:00"
        }
      ],
      "total": 5, "page": 1, "limit": 20
    }
  }
```

#### 文件访问

```
GET /api/v1/files/{document_id}/original
  Header: Authorization: Bearer <access_token>
  Header: Range: bytes=0-1023 (可选，支持分段加载)
  Response: 200 或 206 Partial Content
  Headers: Accept-Ranges: bytes, Content-Type: application/pdf (或对应MIME), Content-Disposition: inline

GET /api/v1/files/{document_id}/thumbnail
  Header: Authorization: Bearer <access_token>
  Response: 缩略图文件流 (默认 200x200, JPEG 格式)
  注: PDF/图片生成实际缩略图，DOCX/Markdown 生成带文件类型标签的图标缩略图
```

#### 健康检查

```
GET /api/v1/health
  Response: { "code": 0, "message": "ok", "data": { "status": "healthy", "db": "ok", "storage": "ok" } }
```

#### 管理接口

```
POST /api/v1/admin/fts-rebuild
  Header: Authorization: Bearer <access_token>
  注: 仅管理员可用，重建 FTS5 全文索引
  Response: { "code": 0, "message": "ok", "data": { "rebuild": true, "document_count": 42 } }
```

#### 预留接口

```
GET /api/v1/chat/
  Response: { "code": 5010, "message": "LLM integration is not available yet.", "data": null }

GET /api/v1/milvus/status
  Response: { "code": 0, "message": "ok", "data": { "status": "not_configured" } }

GET /api/v1/api-keys
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": { "items": [...] } }

POST /api/v1/api-keys
  Header: Authorization: Bearer <access_token>
  Body: { "name": "my-key", "expires_days": 30 }
  Response: { "code": 0, "message": "ok", "data": { "id": 1, "key": "sk-xxxx...", "name": "my-key" } }

DELETE /api/v1/api-keys/{id}
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": null }
```

## 6. 安全策略

### 6.1 密码存储
- 算法: bcrypt (passlib[bcrypt])
- 轮数: 12

### 6.2 JWT 策略
- Access Token: 30 分钟过期
- Refresh Token: 7 天过期
- 签名算法: HS256
- Payload: { "sub": user_id, "type": "access"|"refresh", "iat": ..., "exp": ..., "jti": "uuid" }
- Refresh Token 数据库存储 `jti`（JWT ID），支持精确撤销
- **Token 轮换**: 每次刷新时，旧 Refresh Token 标记 revoked=TRUE，同时签发新 Token
- **Token Family 检测**: 若检测到已撤销的 Refresh Token 被使用，立即撤销该用户所有 Refresh Token
- **登出**: 撤销对应 Refresh Token；Access Token 在过期前仍有效（已知限制，单用户系统风险可接受）
- **JWT_SECRET_KEY**: 至少 256 位随机字符串，使用 `openssl rand -hex 32` 生成，启动时校验长度 >= 32 字节
- **密钥轮换**: 文档说明策略，当前不实现（后续可通过双密钥方案支持）

### 6.3 文件上传安全（三层校验）
- 第一层: 扩展名白名单 (pdf, docx, md, png, jpg, jpeg)
- 第二层: MIME 类型检测 (python-magic 检测魔术字节)
- 第三层: 格式解析验证 (PyMuPDF 能打开 PDF、python-docx 能解析 DOCX、Pillow 能解码图片)
- 大小限制: 50MB (可通过环境变量调整)
- 文件名 UUID 重命名
- 原始文件名仅存数据库

### 6.4 文件访问安全
- 所有文件通过 /api/v1/files/ 端点访问
- 必须携带有效 JWT
- 验证文件属于当前用户 (user_id 绑定)
- 禁止直接暴露 storage/ 目录
- 文件路径使用 pathlib.Path 拼接，验证 resolved_path 仍在 STORAGE_PATH 下（防路径遍历）
- 支持 HTTP Range 请求（206 Partial Content），用于 PDF 在线预览

### 6.5 CORS
- allow_origins: 通过 CORS_ORIGINS 环境变量配置（逗号分隔多个源）
- allow_methods: ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
- allow_headers: ["Authorization", "Content-Type"]
- allow_credentials: True

### 6.6 账户安全
- 登录限流: 5次/分钟/IP
- 账户锁定: 连续失败 10 次后锁定 15 分钟（基于 username 计数）
- 登录失败计数存储在 users 表的 login_failures + locked_until 字段

### 6.7 日志安全
- 禁止记录: 明文密码、JWT Token 全文、API Key 原文
- 允许记录: 用户名、Token 前 8 位（调试关联）、操作类型、IP 地址
- 错误日志中禁止包含完整堆栈中的敏感变量

## 7. 日志系统

- 使用 Python logging 模块
- 格式: `[%(asctime)s] %(levelname)s %(name)s: %(message)s`
- 级别: DEBUG / INFO / WARNING / ERROR / CRITICAL
- 通过 LOG_LEVEL 环境变量控制
- 日志轮转: RotatingFileHandler，按天轮转，保留 30 天
- 审计日志: 登录、文件上传/下载/删除、API Key 创建/删除操作必须记录
- 脱敏规则: 见 6.7 节

## 8. 限流策略

| 端点 | 限流规则 |
|---|---|
| POST /api/v1/auth/login | 5次/分钟/IP |
| POST /api/v1/auth/refresh | 10次/分钟/IP |
| POST /api/v1/documents | 20次/分钟/用户 |
| 其他 GET 接口 | 60次/分钟/用户 |

实现: 基于内存的滑动窗口（单实例够用，未来可换 Redis）
- 数据结构: `dict[tuple[ip, endpoint], deque[timestamp]]`
- 内存回收: 惰性清理（每次请求时清理该 key 的过期记录）
- 局限性: 进程重启后限流状态丢失（可接受）；多实例部署时需切换到 Redis
- 限流中间件接口抽象化，替换存储后端不影响路由层

## 8.1 SQLite 配置

- 启用 WAL 模式: `PRAGMA journal_mode=WAL`
- 启用外键约束: `PRAGMA foreign_keys=ON`
- 数据库文件位置: `./data/app.db`（目录结构中新增 data/ 目录）
- 备份策略: 使用 SQLite `.backup` 命令，非直接文件复制
- 局限性: 单用户/低并发场景适用，触发并发写入瓶颈时迁移至 PostgreSQL

## 9. 扩展点设计

### 9.1 Milvus 向量检索
- 预留接口: GET /api/v1/milvus/status → {"status": "not_configured"}
- 代码位置: backend/services/vector_service.py (TODO: 未来实现)
- 文档入库时，可异步调用 embedding 服务生成向量

### 9.2 LLM 文档问答
- 预留接口: GET /api/v1/chat/ → {"code": 5010, "message": "LLM integration is not available yet."}
- 代码位置: backend/services/chat_service.py (TODO: 未来实现)
- 接收问题 + 文档 ID，返回回答

### 9.3 API Key 管理
- 完整 CRUD 已实现 (model + schema + router)
- API Key 鉴权已接入 middleware (Authorization: Bearer sk-xxx)
- 支持过期时间、活跃状态检查、last_used_at 自动更新
- API Key 以 SHA256 哈希存储，原始 key 仅创建时返回一次

### 9.4 异步任务队列
- 当前: 同步处理文档 (processing_service)
- 结构: processing_service 与路由层完全解耦，未来替换为 Celery task 即可
- processing_service.process_document() 签名兼容 Celery（替换 db 为 scoped_session）
- 每个处理步骤（文本提取、缩略图生成）独立隔离，可拆分为子任务
- 路由层改为 delay() 调用即可切换为异步

## 10. 开发阶段划分

### 阶段1: 核心后端系统
- FastAPI 项目结构
- JWT + Refresh Token
- 文档上传 (安全校验)
- SQLite + Alembic
- 文档 CRUD

### 阶段2: 内容处理 + 搜索
- PDF/DOCX/Markdown 文本提取 (extract_service)
- 全类型缩略图生成 (thumbnail_service: PDF/图片实际渲染, DOCX/MD 带标签图标)
- 文档处理管线模块化 (processing_service: 独立错误隔离, Celery 兼容)
- FTS5 全文搜索 + 查询安全增强 (短语搜索, 控制字符过滤)
- 文档重试机制 (POST /documents/{id}/retry)
- 管理接口 (POST /admin/fts-rebuild)
- status 字段完整生命周期 (queued -> processing -> ready / error)

### 阶段3: 前端 + 扩展 + 部署
- Vue3 + Vite 前端 (Pinia 状态管理, Vue Router, axios 封装)
- 登录页 / 文档列表(含状态标签+重试) / 文档阅读(PDF/图片/Markdown)
- 搜索功能 (FTS5 集成, URL query 参数驱动)
- API Key 鉴权接入 middleware (JWT + API Key 双重支持)
- 预留接口保持 placeholder (chat 5010, milvus not_configured)
- nginx.conf 生产反代 (/storage/ 代理到后鉴权后端)
- run.sh 一键启动 (自动构建前端 + 启动后端)
- FastAPI SPA fallback (前端静态文件直接由后端服务)
- README.md 项目文档
