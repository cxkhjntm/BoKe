# 技术规范文档 - 个人研究资料管理系统

## 1. 技术栈

| 层 | 技术选型 | 版本约束 |
|---|---|---|
| Web 框架 | FastAPI | >=0.100,<1.0 |
| ORM | SQLAlchemy | >=2.0,<3.0 |
| 数据库 | SQLite | 3.x (内置) |
| 迁移 | Alembic | >=1.12,<2.0 |
| 认证 | PyJWT + pwdlib[bcrypt] | >=2.8,<3.0 + >=0.3,<1.0 |
| 任务队列 | Celery + Redis | celery[redis]>=5.3,<6.0; redis>=5.0,<6.0 |
| 文件处理 | python-multipart, Pillow, PyMuPDF, python-docx, python-magic | Pillow>=10.0,<11.0; PyMuPDF>=1.23,<2.0; python-docx>=1.0,<2.0; python-magic>=0.4,<1.0 |
| LLM 集成 | openai, sse-starlette, httpx | openai>=1.30,<2.0; sse-starlette>=2.1,<3.0 |
| RAG | chromadb, langchain-text-splitters | chromadb>=0.5,<1.0; langchain-text-splitters>=0.2,<1.0 |
| 加密 | cryptography (Fernet) | >=42.0,<43.0 |
| 文件锁 | filelock | >=3.13,<4.0 |
| 前端 | Vue3 + Vite, Pinia, Vue Router, axios, marked, dompurify, lucide-vue-next | Vue>=3.4, Vite>=5.4 |
| 反向代理 | Nginx | 1.24+ |

## 2. 项目目录结构

```
BoKe/
├── README.md / README_CN.md
├── DEPLOYMENT.md                # 部署文档
├── docs/
│   └── DEVELOPMENT.md          # 本文档
├── .env.example                 # 环境变量模板
├── requirements.txt
├── run.sh
├── nginx.conf
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app 入口
│   ├── config.py                # 配置（环境变量读取）
│   ├── database.py              # 数据库连接
│   ├── celery_app.py            # Celery 应用配置
│   ├── tasks.py                 # Celery 异步任务
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py              # 用户模型（含头像、背景、轮播设置）
│   │   ├── document.py          # 文档模型
│   │   ├── api_key.py           # API Key 模型
│   │   ├── refresh_token.py     # Refresh Token 模型
│   │   ├── chat_session.py      # 聊天会话模型
│   │   ├── llm_config.py        # LLM 配置模型
│   │   ├── embedding_config.py  # Embedding 配置模型
│   │   ├── rag_config.py        # RAG 配置模型
│   │   ├── user_background.py   # 用户背景图模型
│   │   └── activity.py          # 活动记录模型
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── common.py            # 统一返回结构
│   │   ├── user.py              # 用户相关 Schema
│   │   ├── document.py          # 文档相关 Schema
│   │   ├── api_key.py           # API Key Schema
│   │   ├── chat.py              # 聊天相关 Schema
│   │   ├── llm_config.py        # LLM 配置 Schema
│   │   └── rag.py               # RAG 配置 Schema
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py              # 登录 / 刷新 Token / 登出
│   │   ├── documents.py         # 文档 CRUD + 收藏 + 分类
│   │   ├── search.py            # 搜索接口
│   │   ├── files.py             # 文件访问（鉴权后返回文件）
│   │   ├── chat.py              # LLM 聊天接口（SSE 流式响应）
│   │   ├── chat_sessions.py     # 聊天会话管理
│   │   ├── llm_config.py        # LLM 配置管理
│   │   ├── rag_config.py        # RAG 配置管理
│   │   ├── profile.py           # 用户资料管理（头像、背景、设置）
│   │   ├── dashboard.py         # 仪表盘数据
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
│   │   ├── processing_service.py # 文档处理管线
│   │   ├── chat_service.py      # LLM 聊天服务
│   │   ├── chat_storage.py      # 聊天历史存储（文件锁）
│   │   ├── llm_client.py        # LLM API 客户端（OpenAI 兼容）
│   │   ├── rag_service.py       # RAG 向量检索服务
│   │   └── dashboard_service.py # 仪表盘统计服务
│   ├── middleware/
│   │   ├── __init__.py
│   │   ├── auth.py              # JWT + API Key 中间件
│   │   ├── logging.py           # 请求日志中间件
│   │   └── rate_limit.py        # 限流中间件
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── response.py          # 统一响应工具
│   │   ├── security.py          # 密码哈希、JWT、API Key 工具
│   │   ├── crypto_utils.py      # Fernet 加密（API Key 存储）
│   │   └── logger.py            # 日志配置
│   └── exceptions/
│       ├── __init__.py
│       └── handlers.py          # 统一异常处理
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # 测试 fixtures
│   ├── services/
│   │   ├── test_auth_service.py
│   │   ├── test_extract_service.py
│   │   ├── test_file_service.py
│   │   ├── test_processing_service.py
│   │   ├── test_chat_storage.py
│   │   ├── test_dashboard_service.py
│   │   ├── test_document_service.py
│   │   └── test_chat_service.py
│   ├── api/
│   │   ├── test_auth.py
│   │   ├── test_documents.py
│   │   ├── test_health.py
│   │   ├── test_chat.py
│   │   ├── test_chat_sessions.py
│   │   ├── test_dashboard.py
│   │   ├── test_llm_config.py
│   │   ├── test_profile.py
│   │   └── test_backgrounds.py
│   └── utils/
│       └── test_crypto_utils.py
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   ├── src/
│   │   ├── main.js
│   │   ├── App.vue
│   │   ├── style.css
│   │   ├── router/
│   │   │   └── index.js
│   │   ├── stores/
│   │   │   ├── auth.js          # 认证状态（token、用户信息、背景）
│   │   │   ├── chat.js          # 聊天状态（会话列表、消息）
│   │   │   └── ragConfig.js     # RAG 配置状态
│   │   ├── api/
│   │   │   ├── index.js         # axios 封装 + 拦截器
│   │   │   └── ragConfig.js     # RAG 配置 API
│   │   ├── views/
│   │   │   ├── Login.vue        # 登录页
│   │   │   ├── Dashboard.vue    # 仪表盘
│   │   │   ├── Documents.vue    # 文档列表
│   │   │   ├── Reader.vue       # 文档阅读器
│   │   │   ├── Chat.vue         # LLM 聊天
│   │   │   ├── Categories.vue   # 分类管理
│   │   │   ├── Favorites.vue    # 收藏列表
│   │   │   └── RAGSettings.vue  # RAG 设置
│   │   ├── components/
│   │   │   ├── AppNavbar.vue    # 导航栏
│   │   │   ├── SearchBar.vue    # 搜索栏
│   │   │   ├── SettingsModal.vue # 设置弹窗（头像、背景、轮播）
│   │   │   ├── SettingsDropdown.vue # 设置下拉菜单
│   │   │   ├── StatsCard.vue    # 统计卡片
│   │   │   ├── RecentDocs.vue   # 最近文档
│   │   │   ├── FavoritesTimeline.vue # 收藏时间线
│   │   │   ├── ActivityTimeline.vue # 活动时间线
│   │   │   └── chat/
│   │   │       ├── ChatSidebar.vue      # 聊天侧边栏
│   │   │       ├── ChatMessageList.vue  # 消息列表
│   │   │       ├── ChatInput.vue        # 输入框
│   │   │       ├── ChatConfigPanel.vue  # 配置面板
│   │   │       └── ChatEmptyState.vue   # 空状态
│   │   └── utils/
│   │       └── format.js        # 格式化工具
│   └── public/
└── storage/                     # 运行时生成，不入 Git
    └── {user_id}/
        ├── original/
        ├── thumbnails/
        └── profile/             # 头像、背景图
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
| IMAGE_MAX_UPLOAD_SIZE_MB | 最大图片上传大小(MB) | 2 | 2 |
| IMAGE_ALLOWED_EXTENSIONS | 允许的图片扩展名 | png,jpg,jpeg,webp,gif | png,jpg,jpeg,webp,gif |
| LOG_LEVEL | 日志级别 | INFO | INFO |
| CORS_ORIGINS | 允许的跨域来源 | http://localhost:5173 | http://localhost:5173 |
| RATE_LIMIT_LOGIN | 登录限流(次/分钟/IP) | 5 | 5 |
| REGISTRATION_ENABLED | 是否开放注册 | false | false |
| REDIS_URL | Redis 连接地址 | redis://localhost:6379/0 | redis://localhost:6379/0 |
| CHAT_MAX_TIMEOUT | LLM 响应超时(秒) | 120 | 120 |
| CHAT_MAX_MESSAGE_LENGTH | 单条消息最大长度 | 8000 | 8000 |
| CHAT_RATE_LIMIT_PER_MINUTE | 聊天请求限流(次/分钟/用户) | 20 | 20 |

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
    avatar_path         VARCHAR(500),
    background_path     VARCHAR(500),
    background_opacity  FLOAT DEFAULT 0.3,
    max_rounds          INTEGER DEFAULT 10,
    carousel_interval   INTEGER DEFAULT 5,
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
    jti         VARCHAR(36) UNIQUE NOT NULL,
    expires_at  DATETIME NOT NULL,
    revoked     BOOLEAN DEFAULT FALSE,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_jti ON refresh_tokens(jti);
```

### 4.6 chat_sessions 表

```sql
CREATE TABLE chat_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_id  VARCHAR(36) UNIQUE NOT NULL,
    title       VARCHAR(200) NOT NULL DEFAULT '新会话',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
```

### 4.7 llm_configs 表

```sql
CREATE TABLE llm_configs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    provider    VARCHAR(20) NOT NULL,
    api_key     VARCHAR(500) NOT NULL,       -- Fernet 加密存储
    base_url    VARCHAR(500) NOT NULL,
    model       VARCHAR(100) NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4.8 embedding_configs 表

```sql
CREATE TABLE embedding_configs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    provider    VARCHAR(20) NOT NULL,
    api_key     VARCHAR(500) NOT NULL,
    base_url    VARCHAR(500) NOT NULL,
    model       VARCHAR(100) NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4.9 rag_configs 表

```sql
CREATE TABLE rag_configs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id             INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    chunk_size           INTEGER DEFAULT 500,
    chunk_overlap        INTEGER DEFAULT 50,
    top_k               INTEGER DEFAULT 5,
    score_threshold     FLOAT DEFAULT 0.7,
    created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 4.10 user_backgrounds 表

```sql
CREATE TABLE user_backgrounds (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    image_path  VARCHAR(500) NOT NULL,
    position    INTEGER NOT NULL DEFAULT 0,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_user_backgrounds_user_id ON user_backgrounds(user_id);
```

### 4.11 activities 表

```sql
CREATE TABLE activities (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    action      VARCHAR(50) NOT NULL,
    target_type VARCHAR(50),
    target_id   INTEGER,
    metadata    TEXT,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_activities_user_id ON activities(user_id);
CREATE INDEX idx_activities_created_at ON activities(created_at);
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
  Response: { "code": 0, "message": "ok", "data": { "status": "healthy", "db": "ok", "storage": "ok", "redis": "ok" } }
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
GET /api/v1/milvus/status
  Response: { "code": 0, "message": "ok", "data": { "status": "not_configured" } }
```

#### API Key 管理

```
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

#### 用户资料

```
GET /api/v1/profile
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": { "id": 1, "username": "admin", "avatar_path": "...", ... } }

PUT /api/v1/profile
  Header: Authorization: Bearer <access_token>
  Body: { "background_opacity": 0.5, "max_rounds": 15, "carousel_interval": 10 }
  Response: { "code": 0, "message": "ok", "data": { ... } }

POST /api/v1/profile/avatar
  Header: Authorization: Bearer <access_token>
  Body: multipart/form-data { file: <binary> }
  Response: { "code": 0, "message": "ok", "data": { "avatar_path": "..." } }

DELETE /api/v1/profile/avatar
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": { ... } }

GET /api/v1/profile/backgrounds
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": [{ "id": 1, "image_path": "...", "position": 0 }, ...] }

POST /api/v1/profile/backgrounds
  Header: Authorization: Bearer <access_token>
  Body: multipart/form-data { file: <binary> }
  Response: { "code": 0, "message": "ok", "data": { "id": 1, "image_path": "..." } }

DELETE /api/v1/profile/backgrounds/{id}
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": null }

PUT /api/v1/profile/backgrounds/reorder
  Header: Authorization: Bearer <access_token>
  Body: { "background_ids": [3, 1, 2] }
  Response: { "code": 0, "message": "ok", "data": [...] }
```

#### 仪表盘

```
GET /api/v1/dashboard/stats
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": { "total_documents": 42, "total_size": 1024000, ... } }

GET /api/v1/dashboard/recent
  Header: Authorization: Bearer <access_token>
  Query: limit=5
  Response: { "code": 0, "message": "ok", "data": [{ "id": 1, "title": "...", ... }, ...] }

GET /api/v1/dashboard/top
  Header: Authorization: Bearer <access_token>
  Query: limit=5
  Response: { "code": 0, "message": "ok", "data": [...] }

GET /api/v1/dashboard/activity
  Header: Authorization: Bearer <access_token>
  Query: limit=10
  Response: { "code": 0, "message": "ok", "data": [...] }
```

#### LLM 聊天

```
GET /api/v1/chat/
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": { "status": "available" } }

POST /api/v1/chat/messages/{session_id}
  Header: Authorization: Bearer <access_token>
  Body: { "content": "请总结这篇文档" }
  Response: SSE stream (data: {...}\n\n)
  注: 流式响应，前端使用 ReadableStream 处理
```

#### 聊天会话管理

```
GET /api/v1/chat-sessions
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": [{ "id": 1, "session_id": "uuid", "title": "...", ... }, ...] }

POST /api/v1/chat-sessions
  Header: Authorization: Bearer <access_token>
  Body: { "title": "新会话" }
  Response: { "code": 0, "message": "ok", "data": { "id": 1, "session_id": "uuid", ... } }

PATCH /api/v1/chat-sessions/{session_id}
  Header: Authorization: Bearer <access_token>
  Body: { "title": "新标题" }
  Response: { "code": 0, "message": "ok", "data": { ... } }

DELETE /api/v1/chat-sessions/{session_id}
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": null }

GET /api/v1/chat/messages/{session_id}
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": [{ "role": "user", "content": "..." }, ...] }
```

#### LLM 配置

```
GET /api/v1/llm-config
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": { "provider": "openai", "model": "gpt-4", ... } }

POST /api/v1/llm-config
  Header: Authorization: Bearer <access_token>
  Body: { "provider": "openai", "api_key": "sk-xxx", "base_url": "https://api.openai.com/v1", "model": "gpt-4" }
  Response: { "code": 0, "message": "ok", "data": { ... } }

DELETE /api/v1/llm-config
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": null }
```

#### RAG 配置

```
GET /api/v1/rag-config
  Header: Authorization: Bearer <access_token>
  Response: { "code": 0, "message": "ok", "data": { "chunk_size": 500, "top_k": 5, ... } }

POST /api/v1/rag-config
  Header: Authorization: Bearer <access_token>
  Body: { "chunk_size": 500, "chunk_overlap": 50, "top_k": 5, "score_threshold": 0.7 }
  Response: { "code": 0, "message": "ok", "data": { ... } }
```

## 6. 安全策略

### 6.1 密码存储
- 算法: bcrypt (pwdlib[bcrypt])
- 轮数: 12

### 6.2 JWT 策略
- Access Token: 30 分钟过期 (可通过环境变量配置)
- Refresh Token: 7 天过期 (可通过环境变量配置)
- 签名算法: HS256
- Payload: { "sub": user_id, "type": "access"|"refresh", "iat": ..., "exp": ..., "jti": "uuid" }
- Refresh Token 数据库存储 `jti`（JWT ID），支持精确撤销
- **Token 轮换**: 每次刷新时，旧 Refresh Token 标记 revoked=TRUE，同时签发新 Token
- **Token Family 检测**: 若检测到已撤销的 Refresh Token 被使用，立即撤销该用户所有 Refresh Token
- **登出**: 撤销对应 Refresh Token；Access Token 在过期前仍有效
- **JWT_SECRET_KEY**: 至少 256 位随机字符串，使用 `openssl rand -hex 32` 生成，启动时校验长度 >= 32 字节

### 6.3 API Key 加密
- LLM API Key 使用 Fernet 对称加密存储 (cryptography 库)
- 加密密钥由系统生成并存储在环境变量或配置文件中
- 数据库中存储加密后的密文，解密仅在需要调用 LLM 时进行
- 代码位置: backend/utils/crypto_utils.py

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
- 代码位置: backend/services/rag_service.py (当前使用 ChromaDB)
- 文档入库时，可异步调用 embedding 服务生成向量

### 9.2 LLM 文档问答 (已实现)
- 聊天接口: POST /api/v1/chat/messages/{session_id} (SSE 流式响应)
- 支持 OpenAI 兼容 API (openai, deepseek, siliconflow 等)
- 配置管理: /api/v1/llm-config (CRUD)
- 聊天历史: 文件存储 + filelock (backend/services/chat_storage.py)
- LLM 客户端: backend/services/llm_client.py (httpx 流式调用)
- 前端: Chat.vue + ChatSidebar + ChatMessageList + ChatInput

### 9.3 RAG 向量检索 (已实现)
- 使用 ChromaDB 作为向量数据库
- 文本分割: langchain-text-splitters
- 配置管理: /api/v1/rag-config
- Embedding 配置: /api/v1/embedding-config (如有)
- 服务层: backend/services/rag_service.py

### 9.4 API Key 管理
- 完整 CRUD 已实现 (model + schema + router)
- API Key 鉴权已接入 middleware (Authorization: Bearer sk-xxx)
- 支持过期时间、活跃状态检查、last_used_at 自动更新
- API Key 以 SHA256 哈希存储，原始 key 仅创建时返回一次
- LLM API Key 使用 Fernet 加密存储 (backend/utils/crypto_utils.py)

### 9.5 异步任务队列 (Celery + Redis)
- Celery 应用: `backend/celery_app.py`，Redis 作为 broker 和 result backend
- Celery 任务: `backend/tasks.py`，`process_document_task(document_id)` 创建独立 DB session
- 路由层通过 `_dispatch_processing()` 分发任务，Redis 不可用时自动回退同步处理
- 文档状态流: `queued → processing → ready / error`
- `worker_concurrency=1`（SQLite 单写者限制）
- 前端轮询: Documents.vue 和 Reader.vue 在 `queued`/`processing` 状态下每 3 秒刷新
- run.sh 自动检测 Redis 可用性，可用时启动 Celery worker 后台进程
- 健康检查: `/api/v1/health` 返回 `redis: "ok" | "unavailable" | "not_configured"`

### 9.6 用户个性化 (已实现)
- 头像上传/删除: /api/v1/profile/avatar
- 背景图管理: 最多 10 张，支持轮播
- 轮播间隔配置: carousel_interval (1-60 秒)
- 背景透明度: background_opacity (0-1)
- 消息轮数上限: max_rounds (0=无限制)
- 前端: SettingsModal.vue

### 9.7 仪表盘 (已实现)
- 统计数据: /api/v1/dashboard/stats
- 最近文档: /api/v1/dashboard/recent
- 热门文档: /api/v1/dashboard/top
- 活动时间线: /api/v1/dashboard/activity
- 前端: Dashboard.vue + StatsCard + RecentDocs + ActivityTimeline

### 9.8 文档分类与收藏 (已实现)
- 收藏切换: PATCH /api/v1/documents/{id}/favorite
- 分类设置: PATCH /api/v1/documents/{id}/category
- 分类列表: GET /api/v1/documents/categories
- 收藏列表: GET /api/v1/documents?is_favorite=true
- 前端: Favorites.vue, Categories.vue

```
Upload Request
  → file_service.save_file()
  → document_service.create_document(status="queued")
  → _dispatch_processing()
       ├─ [Redis available] process_document_task.delay(doc_id)
       │     └─ Celery Worker: processing_service.process_document(db, doc)
       │           ├─ extract_service.extract_text()
       │           ├─ thumbnail_service.generate_thumbnail()
       │           └─ status → ready / error
       └─ [Redis unavailable] processing_service.process_document(db, doc) [同步]
```

## 10. 可观测性

### 10.1 请求日志中间件

`backend/middleware/logging.py` — 记录每个 API 请求：

```
[2026-04-30 10:00:00] INFO middleware.logging: POST /api/v1/auth/login 200 45.2ms rid=a1b2c3d4e5f6
```

- 格式: `METHOD PATH STATUS_CODE LATENCY_MS rid=REQUEST_ID`
- 自动生成 `X-Request-ID`（如请求头未携带）
- 排除静态资源请求（`/assets/`）
- 响应头包含 `X-Request-ID` 用于前端关联

### 10.2 认证失败审计日志

`backend/middleware/auth.py` — 所有认证失败场景记录 WARNING 级别日志：

- 无凭证访问
- Token 过期
- Token 无效
- Token 类型错误
- 用户不存在或已禁用
- API Key 无效/过期/已禁用

日志包含客户端 IP 地址（支持 X-Forwarded-For）。

### 10.3 异常处理日志

`backend/exceptions/handlers.py`：

- 4xx AppException: WARNING 级别
- 5xx AppException: ERROR 级别
- 未处理异常: ERROR 级别（含堆栈）
- HTTPException: 统一响应格式处理

### 10.4 限流响应头

限流中间件返回 `X-RateLimit-Limit` 和 `X-RateLimit-Remaining` 响应头：

```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 3
```

触发限流时返回 HTTP 429 + `{"code": 4029, "message": "Too many requests"}`。

## 11. 测试

### 11.1 测试框架

- pytest >= 8.0
- pytest-cov >= 5.0 (覆盖率报告)
- httpx >= 0.27 (FastAPI TestClient)

### 11.2 运行测试

```bash
# 运行全部测试
pytest tests/ -v

# 运行服务层单元测试
pytest tests/services/ -v

# 运行 API 集成测试
pytest tests/api/ -v

# 查看覆盖率报告
pytest tests/ --cov=backend --cov-report=term-missing
```

### 11.3 测试结构

```
tests/
├── conftest.py              # 共享 fixtures
├── services/                # 服务层单元测试
│   ├── test_auth_service.py     # 认证、Token 刷新、登出、账户锁定
│   ├── test_extract_service.py  # PDF/DOCX/MD 文本提取
│   ├── test_file_service.py     # 文件保存/删除/路径遍历防护
│   ├── test_processing_service.py # 处理管线
│   ├── test_chat_storage.py     # 聊天历史存储
│   ├── test_dashboard_service.py # 仪表盘统计
│   ├── test_document_service.py # 文档业务逻辑
│   └── test_chat_service.py     # LLM 聊天服务
├── api/                     # API 集成测试
│   ├── test_auth.py             # 登录/刷新/登出端点
│   ├── test_documents.py        # 文档 CRUD + 上传 + 重试
│   ├── test_health.py           # 健康检查端点
│   ├── test_chat.py             # LLM 聊天端点
│   ├── test_chat_sessions.py    # 聊天会话管理
│   ├── test_dashboard.py        # 仪表盘端点
│   ├── test_llm_config.py       # LLM 配置端点
│   ├── test_profile.py          # 用户资料端点
│   └── test_backgrounds.py      # 背景图管理端点
└── utils/                   # 工具函数测试
    └── test_crypto_utils.py     # Fernet 加密/解密
```

### 11.4 测试 Fixtures

| Fixture | 作用域 | 说明 |
|---------|--------|------|
| `tmp_storage` | session | 临时存储目录 |
| `db_engine` | function | 每个测试独立的 SQLite 数据库 |
| `db_session` | function | 事务性数据库 session（自动回滚） |
| `client` | function | FastAPI TestClient（DB + 存储覆盖） |
| `admin_user` | function | 创建测试管理员用户 |
| `auth_headers` | function | 有效 JWT Bearer Token |
| `sample_pdf` | function | 最小有效 PDF 文件 |
| `sample_docx` | function | 最小有效 DOCX 文件 |
| `sample_markdown` | function | 最小 Markdown 文件 |
| `sample_image` | function | 最小有效 PNG 图片 |

### 11.5 覆盖率目标

- 服务层: >= 80%
- API 层: >= 70%
- 总体: >= 60%

## 12. 开发阶段划分

### 阶段 A: 核心后端系统 ✅
- FastAPI 项目结构
- JWT + Refresh Token (Token 轮换 + Family 检测)
- 文档上传 (三层安全校验)
- SQLite + Alembic
- 文档 CRUD

### 阶段 B: 内容处理 + 搜索 ✅
- PDF/DOCX/Markdown 文本提取 (extract_service)
- 全类型缩略图生成 (thumbnail_service)
- 文档处理管线模块化 (processing_service)
- FTS5 全文搜索 + 查询安全增强
- 文档重试机制 (POST /documents/{id}/retry)
- 管理接口 (POST /admin/fts-rebuild)

### 阶段 C: 异步任务队列 ✅
- Celery + Redis 异步文档处理
- Redis 不可用时自动回退同步处理
- 前端轮询状态更新 (3 秒间隔)
- run.sh 自动检测 Redis + 启动 Celery worker

### 阶段 D: 可观测性 + 测试 + 安全加固 ✅
- 请求日志中间件 (X-Request-ID 关联)
- 认证失败审计日志
- 限流响应头 (X-RateLimit-Limit / X-RateLimit-Remaining)
- pytest 测试基础设施
- 服务层单元测试 + API 集成测试

### 阶段 E: 前端 + LLM + RAG + 用户系统 ✅
- Vue3 + Vite 前端 (Pinia, Vue Router, axios)
- 登录页 / 仪表盘 / 文档列表 / 文档阅读器
- LLM 聊天功能 (SSE 流式响应, OpenAI 兼容)
- RAG 向量检索 (ChromaDB + langchain-text-splitters)
- 聊天会话管理 (CRUD + 历史存储)
- LLM/RAG 配置管理
- 用户资料 (头像、背景图、轮播、透明度)
- 文档收藏 + 分类
- API Key 鉴权 (JWT + API Key 双重支持)
- nginx.conf 生产反代
- run.sh 一键启动
