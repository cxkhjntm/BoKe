# BoKe 大模型问答功能 — 多角色评审整合纪要

> 日期：2026-05-07
> 对应方案：llm_chat_implementation_plan_v1.md
> 参与评审：系统架构师、后端工程师、前端工程师、DevOps工程师、安全工程师

---

## 一、各角色核心意见摘要

### 1. 系统架构师（architect_analysis.md — 23,931 字节）

**关键产出：**
- 功能分解为 F1~F8，与现有模块精确映射
- 变更清单：12 个新增文件、7 个修改文件
- 新增错误码规划：4003（无权限）、4005（配置未设置）、4006（LLM调用失败）、4007（流式输出异常）、4008（消息过长）、4009（会话已过期）
- RAG 扩展设计：`RAGContextProvider` 抽象接口、Prompt 模板预留、Chroma 集成 3 步路径
- 原子写策略：`.tmp` + `replace()` 已覆盖

**与 v1.0 方案的差异：**
- 架构师使用 `llm_max_rounds` 作为字段名（v1.0 用 `max_rounds`）
- 建议新增 `status` 字段到 chat_sessions（如 active/archived）

### 2. 后端工程师（backend_analysis.md — 40,395 字节）

**关键产出：**
- 新增 8 个后端文件、修改 5 个文件
- 服务层拆分为：`llm_config_service.py`、`llm_client.py`、`chat_service.py`、`chat_storage.py`
- 数据库：`llm_configs` 表包含 `max_rounds` 字段（v1.0 放在 `users` 表）
- **POSIX 文件锁**：推荐 `fcntl`（Linux）或 `filelock` 库保护 JSON 并发写
- **Alembic 陷阱提醒**：`alembic/env.py` 必须 import 新增 Model，否则 autogenerate 不识别
- 大模型调用使用 `httpx.AsyncClient.stream()` 原生实现，给出完整伪代码
- 单会话消息上限建议 50 轮（v1.0 用用户配置的 max_rounds）

**与 v1.0 方案的差异：**
- 服务层拆分更细（llm_config_service + llm_client + chat_storage）
- max_rounds 放在 llm_configs 表而非 users 表
- 强调文件锁必要性

### 3. 前端工程师（frontend_analysis.md — 18,742 字节）

**关键产出：**
- 新增 10 个文件、修改 4 个文件
- 组件目录建议 `frontend/src/components/chat/` 子目录组织
- 新增 `useChatStream.js` composable 封装 SSE 流式逻辑
- 新增 `utils/markdown.js` 工具封装 marked + DOMPurify
- 移动端 Sidebar 采用 drawer 模式
- 消息渲染复用现有 `marked` + `DOMPurify`
- UI 风格完全对齐：glassmorphism、CSS 变量、骨架屏、空状态

**与 v1.0 方案的差异：**
- 组件拆分更细（增加 ChatMessageItem、ChatEmptyState）
- 推荐 composable 方式解耦 SSE 逻辑
- 与 v1.0 设计高度一致，无冲突

### 4. DevOps工程师（devops_analysis.md — 11,406 字节）

**关键产出：**
- 推荐 `sse-starlette>=2.1` 作为 SSE 封装（v1.0 用原生 StreamingResponse）
- 新增 Python 依赖：`openai>=1.30` + `sse-starlette>=2.1`
- **大量全局环境变量建议**：`LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`、`SESSIONS_PATH` 等
- nginx SSE 配置：独立 location、关闭 buffering、超时 300s
- 目录权限：`sessions/` 建议 750

**与 v1.0 方案的差异（需裁定）：**
- DevOps 偏向全局环境变量配置大模型 API，但用户需求是"在问答页面配置 API"（用户级配置）
- v1.0 的 `CHAT_*` 环境变量更轻量（仅超时/限流/长度），不存储 API Key

### 5. 安全工程师（security_analysis.md）

**关键产出：**
- **4 项 CRITICAL**：跨用户访问、API Key 明文存储、SSRF、Prompt 注入
- **5 项 HIGH**：会话劫持、并发写冲突、超长消息、无速率限制、SSE 连接耗尽
- 加密建议：**AES-256-GCM**（v1.0 用 Fernet/AES-128-CBC）
- 速率限制：单用户 10 次/分钟，SSE 3 并发
- 文件权限：`0o700` 目录 + `0o600` 文件
- 红线：禁止明文存储 API Key、禁止无白名单自定义 Base URL、禁止日志记录密钥

**与 v1.0 方案的差异：**
- 加密强度要求更高（AES-256-GCM vs Fernet）
- 速率限制更严格（10/min vs 30/min）
- 建议文件权限更严格（0o700 vs 默认）

---

## 二、关键差异裁定（架构师最终裁决）

### 2.1 max_rounds 字段位置

| 选项 | 支持者 | 理由 |
|------|--------|------|
| `users.max_rounds` | v1.0 方案 | 属于用户个人设置，与 carousel_interval 同级 |
| `llm_configs.max_rounds` | 后端工程师 | 与 LLM 配置强相关，换模型时可独立调整 |

**裁定：`users.max_rounds`**
- **理由**：用户需求原文是"个人设置里可以调消息轮数上限"，明确属于用户级设置而非模型级设置。users 表已有 `carousel_interval`、`background_opacity` 等用户偏好字段，max_rounds 属于同一语义层。如果未来需要按模型配置轮数，可再扩展 `llm_configs.max_rounds` 覆盖用户默认值。

### 2.2 API Key 存储加密算法

| 选项 | 支持者 | 理由 |
|------|--------|------|
| Fernet (AES-128-CBC) | v1.0 方案 | 简单、Python 内置 cryptography 支持、密钥派生自 JWT_SECRET_KEY |
| AES-256-GCM | 安全工程师 | 更高强度、支持认证加密、符合现代安全标准 |

**裁定：AES-256-GCM**
- **理由**：安全工程师的 CRITICAL 评级合理。`cryptography` 库已引入（DevOps 也推荐），实现成本接近。使用 AES-256-GCM 配合 `os.urandom(12)` nonce，密钥通过 `hashlib.pbkdf2_hmac('sha256', JWT_SECRET_KEY.encode(), b'llm-salt', 100000, dklen=32)` 派生。

### 2.3 环境变量设计：全局 vs 用户级

| 选项 | 支持者 | 理由 |
|------|--------|------|
| 用户级配置（数据库存储） | v1.0 方案、用户需求 | 每个用户在页面内独立配置自己的 API Key |
| 全局环境变量 | DevOps | 统一管理、部署简单 |

**裁定：用户级配置（数据库存储 + 加密）**
- **理由**：用户需求原文"支持在当前问答页面配置硅基流动或deepseek的API"明确是多用户各自配置。全局环境变量违背需求。仅保留轻量全局变量：`CHAT_MAX_TIMEOUT`、`CHAT_MAX_MESSAGE_LENGTH`、`CHAT_RATE_LIMIT_PER_MINUTE`。

### 2.4 速率限制阈值

| 选项 | 支持者 | 理由 |
|------|--------|------|
| 30 次/分钟/IP | v1.0 方案 | 兼顾正常使用和防护 |
| 10 次/分钟/用户 + SSE 3 并发 | 安全工程师 | 更严格，防滥用和连接耗尽 |

**裁定：20 次/分钟/用户，SSE 单用户并发 2**
- **理由**：10 次/分钟对正常聊天偏严格（用户可能快速追问）。20 次/分钟是合理折中。SSE 并发限制为 2（单用户最多同时 2 个流式请求），防止连接耗尽。

### 2.5 SSE 实现方式

| 选项 | 支持者 | 理由 |
|------|--------|------|
| 原生 StreamingResponse | v1.0 方案 | 轻量、无额外依赖 |
| sse-starlette | DevOps、后端 | FastAPI 生态标准、格式更规范 |

**裁定：sse-starlette**
- **理由**：`sse-starlette>=2.1` 与 FastAPI 集成成熟，自动处理 SSE 格式（event/data/id/retry），减少手写格式错误风险。依赖已计划引入，成本极低。

### 2.6 服务层拆分粒度

| 选项 | 支持者 | 理由 |
|------|--------|------|
| 合并 chat_service.py | v1.0 方案 | 减少文件数量，JSON IO + LLM 调用 + 裁剪逻辑在同一文件 |
| 拆分为 4 个服务文件 | 后端工程师 | 职责单一、测试隔离、替换 LLM 客户端时影响面小 |

**裁定：拆分为 `chat_service.py` + `chat_storage.py` + `llm_client.py`**
- **理由**：
  - `chat_storage.py`：JSON 文件 IO（含文件锁、路径安全、原子写）
  - `llm_client.py`：大模型 API 调用封装（OpenAI-compatible，流式返回）
  - `chat_service.py`：业务编排（读取历史 → 追加 → 调用 llm_client → 保存 → 裁剪）
  - llm_config 的 CRUD 较简单，直接放在 router 层，不单独拆 service（避免过度设计）

### 2.7 文件锁机制

| 选项 | 支持者 | 理由 |
|------|--------|------|
| 原子写（.tmp + replace） | v1.0 方案 | 单实例下足够 |
| POSIX 文件锁（fcntl/filelock） | 后端、安全 | 多 worker / 多标签页并发保护 |

**裁定：原子写 + `filelock` 库**
- **理由**：BoKe 部署方式通常是单实例 uvicorn（`--workers 1`），原子写已解决大部分问题。但用户可能在多个标签页同时操作同一会话，引入 `filelock`（跨平台，比 fcntl 更兼容）成本极低，且满足安全工程师的 HIGH 风险评级。

---

## 三、方案 v1.1 关键更新清单

基于以上裁定，对 v1.0 方案的更新如下：

### 3.1 数据库更新

1. `users.max_rounds` 字段保留（裁定 2.1）
2. `llm_configs` 表不包含 `max_rounds`（移除后端工程师建议的该字段）
3. `llm_configs.api_key` 字段类型扩充到 `String(500)` 以容纳加密后密文 + nonce + tag

### 3.2 依赖更新

requirements.txt 新增：
```
openai>=1.30,<2.0
sse-starlette>=2.1,<3.0
cryptography>=42.0,<43.0
filelock>=3.13,<4.0
```

### 3.3 加密方案更新

替换 Fernet 为 AES-256-GCM：
```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import hashlib

def _derive_key() -> bytes:
    return hashlib.pbkdf2_hmac('sha256', JWT_SECRET_KEY.encode(), b'bo-ke-llm-v1', 100000, dklen=32)

def encrypt_api_key(plain: str) -> str:
    nonce = os.urandom(12)
    ct = AESGCM(_derive_key()).encrypt(nonce, plain.encode(), None)
    return base64.b64encode(nonce + ct).decode()

def decrypt_api_key(cipher: str) -> str:
    raw = base64.b64decode(cipher.encode())
    nonce, ct = raw[:12], raw[12:]
    return AESGCM(_derive_key()).decrypt(nonce, ct, None).decode()
```

### 3.4 服务层文件更新

新增 `backend/services/chat_storage.py`（文件锁 + 路径安全 + 原子写）：
```python
import json, fcntl, os
from pathlib import Path
from filelock import FileLock
from backend.config import BASE_DIR

SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

def _session_path(user_id: int, session_id: str) -> Path:
    d = SESSIONS_DIR / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    os.chmod(d, 0o700)
    p = (d / f"{session_id}.json").resolve()
    if not p.is_relative_to(SESSIONS_DIR.resolve()):
        raise ValueError("Path traversal detected")
    return p

def load_messages(user_id: int, session_id: str) -> list[dict]:
    path = _session_path(user_id, session_id)
    if not path.exists():
        return []
    with FileLock(str(path) + ".lock"):
        return json.loads(path.read_text(encoding="utf-8"))

def save_messages(user_id: int, session_id: str, messages: list[dict]) -> None:
    path = _session_path(user_id, session_id)
    tmp = path.with_suffix(".tmp")
    with FileLock(str(path) + ".lock"):
        tmp.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")
        os.chmod(tmp, 0o600)
        tmp.replace(path)
```

### 3.5 SSE 路由更新

使用 `sse-starlette`：
```python
from sse_starlette.sse import EventSourceResponse

async def event_generator():
    yield {"event": "start", "data": json.dumps({"type": "start"})}
    # ... delta events
    yield {"event": "finish", "data": json.dumps({"type": "finish", "content": full})}

return EventSourceResponse(event_generator())
```

### 3.6 速率限制更新

```python
# main.py RateLimitMiddleware
rules = {
    "/api/v1/auth/login": (RATE_LIMIT_LOGIN, 60),
    "/api/v1/auth/refresh": (10, 60),
    "/api/v1/chat/messages/": (20, 60),  # 单 IP 20 次/分钟
}
```

### 3.7 nginx 配置更新

```nginx
location /api/v1/chat/messages/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}
```

### 3.8 Alembic 注意事项

- `alembic/env.py` 必须添加 `from backend.models import llm_config, chat_session`（或确保 `backend/models/__init__.py` 被 import）
- 迁移脚本使用 `sa.Column(..., server_default=sa.text("10"))` 为 `users.max_rounds` 设置默认值

---

## 四、风险重评估

| 风险 | v1.0 评级 | 评审后评级 | 应对措施 |
|------|----------|-----------|---------|
| 跨用户会话访问 | 高 | **CRITICAL** | 所有接口强制 user_id 校验 + UUID session_id |
| API Key 泄露 | 高 | **CRITICAL** | AES-256-GCM 加密 + 日志脱敏 + 内存即用即清 |
| SSRF | 中 | **CRITICAL** | Base URL 白名单（硅基流动/DeepSeek 域名） |
| Prompt 注入 | 中 | **CRITICAL** | system prompt 固定，用户消息独立字段 |
| 并发写冲突 | 中 | **HIGH** | filelock + 原子写 |
| 速率绕过 | 低 | **HIGH** | 20/min/IP + SSE 单用户并发 2 |
| SSE 连接耗尽 | 中 | **HIGH** | nginx 超时 + 应用层并发限制 |
| JSON 文件损坏 | 中 | MEDIUM | filelock + 原子写已覆盖 |

---

## 五、执行计划微调

### 5.1 Agent 分工微调

| Agent | 调整内容 |
|-------|---------|
| `backend-core-dev` (A1) | 增加 `chat_storage.py` 文件锁实现；`users.max_rounds` 而非 `llm_configs.max_rounds`；`alembic/env.py` import 提醒 |
| `backend-chat-dev` (A2) | 使用 `sse-starlette` 替代原生 StreamingResponse；使用 `chat_storage.py` 而非内嵌文件 IO |
| `security-dev` (A5) | 实现 AES-256-GCM 而非 Fernet；Base URL 白名单校验；目录权限 0o700/0o600 |
| `devops-dev` (A7) | 仅新增 `openai`/`sse-starlette`/`cryptography`/`filelock`；不新增全局 LLM_* 环境变量；nginx 配置微调 |

### 5.2 阶段化实施微调

```
Stage 1 (feature/stage1-core)
├── A1: 迁移 + 模型 + schemas + llm_config/chat_sessions 路由 + chat_storage 文件锁
└── A2: chat 路由 SSE（sse-starlette）+ llm_client 流式调用

Stage 2 (feature/stage2-ui)
└── A3: Chat.vue + components/chat/* + useChatStream composable + router/api/store

Stage 3 (feature/stage3-settings)
└── A4: profile max_rounds + SettingsModal slider

Stage 4 (feature/stage4-polish)
├── A5: AES-256-GCM 加密 + SSRF 白名单 + 限流 + 文件权限
├── A6: pytest 全量覆盖（含文件锁、加密解密、跨用户拦截）
└── A7: nginx SSE location + requirements + .env.example
```

---

## 六、结论

经 5 角色并行评审后，v1.0 方案在技术架构和模块划分上获得一致认可。主要调整集中在：

1. **安全加固**：加密算法升级为 AES-256-GCM，增加 filelock 并发保护，SSRF 白名单，速率限制收紧。
2. **技术选型**：SSE 采用 `sse-starlette`，增加 `filelock` 依赖。
3. **数据模型**：`max_rounds` 明确放在 `users` 表，保持用户设置语义一致性。
4. **服务拆分**：JSON 文件 IO 独立为 `chat_storage.py`，LLM 调用独立为 `llm_client.py`。

所有调整均可在现有方案框架内平滑落地，不破坏已定义的 API 契约和模块边界。

---

*评审整合：系统架构师（Team Lead）*
*参与角色：系统架构师、后端工程师、前端工程师、DevOps工程师、安全工程师*
