# BoKe 大模型问答功能 — 功能实施方案 v1.0

> 制定日期：2026-05-07
> 适用分支：feature/llm-chat
> 关联需求：大模型问答页面、硅基流动/DeepSeek API配置、会话管理、消息轮数上限、JSON文件存储

---

## 1. 方案概述

### 1.1 目标
为 BoKe 增加一套完整的大模型问答（LLM Chat）模块，支持：
1. 在问答页面内配置硅基流动（SiliconFlow）或 DeepSeek 的 API Key、Base URL、Model。
2. 会话级管理：增删查改、切换当前会话。
3. 个人设置中可调消息轮数上限（0~30，0表示无限制）。
4. 每个会话以 JSON 文件形式持久化消息数组，路径为 `sessions/{user_id}/{session_id}.json`。
5. 聊天流程：读取历史 → 追加用户消息 → 调用外部 LLM（流式SSE） → 追加助手回复 → 按上限裁剪 → 写回文件。
6. 预留 RAG 扩展接口，后续可无缝接入 Chroma 向量检索。

### 1.2 设计原则
- **零破坏**：不修改现有认证、文档、搜索、文件等业务逻辑。
- **用户隔离**：所有会话文件、配置、消息严格绑定 `user_id`。
- **轻量持久化**：会话消息用 JSON 文件存储（而非数据库存储大文本），降低 SQLite 压力，同时方便后续 RAG 对单文件做向量化。
- **流式体验**：聊天回复使用 SSE（Server-Sent Events），前端实时渲染。
- **统一风格**：API 响应沿用 `{code, message, data}`；前端 UI 复用现有 CSS 变量与组件模式。

---

## 2. 当前项目架构要点总结

| 维度 | 现状 |
|------|------|
| 后端框架 | FastAPI 0.100+，Python 3.11+ |
| ORM / DB | SQLAlchemy 2.0 + SQLite（WAL模式）+ Alembic 迁移 |
| 认证 | JWT（HS256，Bearer Token）+ API Key（sk-xxx，SHA256） |
| 响应格式 | `ok(data)` / `fail(code, message)` → `{code, message, data}` |
| 文件存储 | `storage/{user_id}/{subfolder}/`（file_service.py 统一管理） |
| 前端 | Vue 3 + Vite + Pinia + Vue Router + Axios |
| 已有预留 | `chat.py` 返回 501；`milvus.py` 预留向量数据库 |
| 测试 | pytest + TestClient，覆盖率基线 80%+ |
| 部署 | run.sh（venv + alembic + frontend build + uvicorn）+ nginx.conf |

---

## 3. 变更范围与影响分析

### 3.1 文件变更树状图

```
BoKe/
├── backend/
│   ├── config.py                    [MODIFY]  新增 CHAT_ 配置项
│   ├── main.py                      [MODIFY]  注册新 routers（llm_config, chat_sessions, chat）
│   ├── models/
│   │   ├── __init__.py              [MODIFY]  导出 LLMConfig, ChatSession
│   │   ├── llm_config.py            [NEW]     大模型配置表
│   │   └── chat_session.py          [NEW]     会话元数据表
│   ├── schemas/
│   │   ├── __init__.py              [MODIFY]  导出新 schemas
│   │   ├── llm_config.py            [NEW]     配置 CRUD schemas
│   │   └── chat.py                  [NEW]     聊天/会话 schemas
│   ├── routers/
│   │   ├── __init__.py              [MODIFY]  无实质变更（main.py直接import）
│   │   ├── chat.py                  [MODIFY]  由占位符改为完整聊天SSE接口
│   │   ├── llm_config.py            [NEW]     大模型配置管理接口
│   │   └── chat_sessions.py         [NEW]     会话元数据 CRUD
│   ├── services/
│   │   ├── __init__.py              [MODIFY]  导出 chat_service
│   │   └── chat_service.py          [NEW]     聊天核心逻辑：文件IO、LLM调用、裁剪
│   └── utils/
│       └── response.py              [NO CHANGE]
├── frontend/
│   ├── src/
│   │   ├── router/index.js          [MODIFY]  新增 /chat 路由
│   │   ├── api/index.js             [MODIFY]  新增聊天相关 API 封装
│   │   ├── stores/
│   │   │   └── chat.js              [NEW]     聊天状态管理（Pinia）
│   │   ├── views/
│   │   │   └── Chat.vue             [NEW]     聊天主页面（含侧边栏会话列表+对话区）
│   │   └── components/
│   │       ├── AppNavbar.vue        [MODIFY]  导航栏新增"AI对话"入口
│   │       ├── SettingsModal.vue    [MODIFY]  增加"消息轮数上限" slider
│   │       ├── ChatSidebar.vue      [NEW]     会话侧边栏（增删切）
│   │       ├── ChatConfigPanel.vue  [NEW]     API配置面板（提供商/Key/模型）
│   │       ├── ChatMessageList.vue  [NEW]     消息列表（流式渲染）
│   │       └── ChatInput.vue        [NEW]     底部输入框
│   └── package.json                 [NO CHANGE] 无需新增前端依赖
├── alembic/versions/
│   └── 007_add_llm_chat.py          [NEW]     新增 llm_configs / chat_sessions 表
├── sessions/                        [NEW DIR] 运行时自动创建，同级于 storage/
│   └── {user_id}/
│       └── {session_id}.json
├── requirements.txt                 [MODIFY]  新增 httpx, openai
├── nginx.conf                       [MODIFY]  SSE 相关超时与 buffering
└── tests/
    ├── api/test_chat.py             [NEW]
    ├── api/test_llm_config.py       [NEW]
    ├── api/test_chat_sessions.py    [NEW]
    └── services/test_chat_service.py [NEW]
```

### 3.2 影响面评估

| 模块 | 影响等级 | 说明 |
|------|---------|------|
| 用户认证 | 无 | 复用 `get_current_user`，无变更 |
| 文档管理 | 无 | 完全独立模块 |
| 文件存储 | 低 | 仅新增 `sessions/` 目录，复用现有路径安全校验逻辑 |
| 数据库 | 中 | 新增两张表，Alembic 自动迁移 |
| 前端路由 | 低 | 新增一条 `/chat` 路由 |
| 前端状态 | 低 | 新增独立 Pinia store，不干扰 auth store |
| 部署 | 低 | 新增两个 pip 依赖，nginx 微调 SSE 参数 |

---

## 4. 数据库变更

### 4.1 新增表：llm_configs

存储每个用户的大模型 API 配置。每个用户目前仅支持一条活跃配置（单用户单配置简化设计，后续如需多配置可扩展为一对多）。

```sql
CREATE TABLE llm_configs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    provider    VARCHAR(20) NOT NULL,  -- 'siliconflow' | 'deepseek'
    api_key     VARCHAR(255) NOT NULL,  -- 加密存储（见安全章节）
    base_url    VARCHAR(500) NOT NULL,
    model       VARCHAR(100) NOT NULL,
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_llm_configs_user_id ON llm_configs(user_id);
CREATE UNIQUE INDEX idx_llm_configs_user_id_unique ON llm_configs(user_id); -- 单用户单配置
```

### 4.2 新增表：chat_sessions

存储会话元数据（不存储消息正文，正文在 JSON 文件中）。

```sql
CREATE TABLE chat_sessions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,
    session_id  VARCHAR(36) NOT NULL UNIQUE,  -- UUID，也是 JSON 文件名
    title       VARCHAR(200) NOT NULL DEFAULT '新会话',
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_sessions_updated_at ON chat_sessions(updated_at);
```

### 4.3 修改表：users

在个人设置中增加消息轮数上限字段，直接复用 `ProfileUpdate` 和 `ProfileOut`。

```sql
ALTER TABLE users ADD COLUMN max_rounds INTEGER DEFAULT 10 CHECK(max_rounds >= 0 AND max_rounds <= 30);
```

> 默认值 10 轮（20 条消息），用户可在 SettingsModal 中通过 slider 调整 0~30。0 表示不限制。

### 4.4 Alembic 迁移文件

路径：`alembic/versions/007_add_llm_chat.py`

- 遵循现有迁移风格（参照 `006_add_category.py`）。
- `upgrade()` 依次创建 `llm_configs`、`chat_sessions`，并给 `users` 添加 `max_rounds`。
- `downgrade()` 逆序删除（先删索引，再删表/列）。

---

## 5. API 规范

### 5.1 大模型配置管理 `llm_config.py`

前缀：`/api/v1/llm-config`

#### GET /
获取当前用户的大模型配置。

**Response (200)**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "id": 1,
    "provider": "siliconflow",
    "api_key": "sk-sfxx...xxxx",
    "base_url": "https://api.siliconflow.cn/v1",
    "model": "deepseek-ai/DeepSeek-V3",
    "created_at": "2026-05-07T10:00:00",
    "updated_at": "2026-05-07T10:00:00"
  }
}
```
> `api_key` 返回脱敏形式（前8位 + *** + 后4位），前端展示用。如未配置则 `data: null`。

#### POST /
创建或更新配置（单用户单配置， Upsert 语义）。

**Request**
```json
{
  "provider": "siliconflow",
  "api_key": "sk-sfxxxxxxxxxxxxxxxx",
  "base_url": "https://api.siliconflow.cn/v1",
  "model": "deepseek-ai/DeepSeek-V3"
}
```

**Validation**
- `provider`: enum `['siliconflow', 'deepseek']`
- `api_key`: min_length=10
- `base_url`: 合法 URL
- `model`: min_length=1

**Response (200)**
```json
{
  "code": 0,
  "message": "ok",
  "data": { "id": 1, "provider": "siliconflow", ... }
}
```

#### DELETE /
删除当前用户的配置。

**Response (200)**
```json
{ "code": 0, "message": "ok", "data": null }
```

### 5.2 会话管理 `chat_sessions.py`

前缀：`/api/v1/chat-sessions`

#### GET /
获取当前用户的所有会话列表，按 `updated_at` 降序。

**Response (200)**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [
      { "id": 1, "session_id": "550e8400-e29b-41d4-a716-446655440000", "title": "如何安装产品", "updated_at": "..." }
    ]
  }
}
```

#### POST /
创建新会话。

**Request**
```json
{ "title": "新会话" }
```

**Response (200)**
```json
{
  "code": 0,
  "message": "ok",
  "data": { "id": 1, "session_id": "...", "title": "新会话", "created_at": "..." }
}
```

#### PATCH /{session_id}
修改会话标题。

**Request**
```json
{ "title": "重命名后的标题" }
```

#### DELETE /{session_id}
删除会话（同时删除对应的 JSON 文件）。

**Response (200)**
```json
{ "code": 0, "message": "ok", "data": null }
```

### 5.3 聊天与消息 `chat.py`

前缀：`/api/v1/chat`

#### GET /messages/{session_id}
获取某个会话的完整消息历史。

**Response (200)**
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "session_id": "...",
    "messages": [
      { "role": "system", "content": "你是一个有帮助的助手。" },
      { "role": "user", "content": "你好" },
      { "role": "assistant", "content": "你好！有什么可以帮你的？" }
    ]
  }
}
```

#### POST /messages/{session_id}
发送消息并流式返回助手回复（SSE）。

**Request**
```json
{ "content": "请介绍这个产品" }
```

**Response (SSE)**
```
HTTP/1.1 200 OK
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
Connection: keep-alive

event: message
data: {"type":"start","session_id":"..."}

event: message
data: {"type":"delta","content":"请"}

event: message
data: {"type":"delta","content":"先将"}

event: message
data: {"type":"finish","content":"请将产品包解压后...","usage":{...}}
```

**服务端内部流程：**
1. 鉴权 + 校验 `session_id` 归属当前用户。
2. 读取 `sessions/{user_id}/{session_id}.json`。
3. 追加 `{role: "user", content}`。
4. 读取用户 `llm_config`，如未配置返回 `4000` 错误。
5. 调用外部 LLM API（`httpx` 流式请求，OpenAI-compatible 格式）。
6. 边接收边 SSE 推送给前端。
7. 接收完毕后，追加 `{role: "assistant", content: full_content}` 到 JSON。
8. 按 `max_rounds` 裁剪：保留最近 `max_rounds * 2` 条消息（若 `max_rounds > 0`）。
9. 原子写回 JSON 文件。

### 5.4 个人设置扩展 `profile.py`

#### PUT / 扩展字段
`ProfileUpdate` schema 增加 `max_rounds: int | None = Field(default=None, ge=0, le=30)`。

---

## 6. 关键交互流程

### 6.1 首次进入聊天页面

```
用户点击"AI对话"
  → 前端 GET /api/v1/chat-sessions
  → 若 items 为空，自动 POST /api/v1/chat-sessions 创建默认会话
  → 前端 GET /api/v1/chat/messages/{session_id}
  → 渲染消息列表
```

### 6.2 发送消息（流式）

```
用户输入内容，点击发送
  → 前端立即在本地 messages 数组追加 user 消息（乐观更新）
  → 前端建立 EventSource: POST /api/v1/chat/messages/{session_id}
  → 后端读取 JSON 文件 → 追加 user 消息
  → 后端调用 LLM API（httpx stream）
  → 后端 SSE 推送 delta 片段
  → 前端逐字渲染 assistant 消息
  → 流结束，后端追加 assistant 完整消息到 JSON → 裁剪 → 写回
  → 前端收到 finish 事件，关闭 EventSource
```

### 6.3 配置大模型 API

```
用户点击配置图标
  → 前端展示 ChatConfigPanel（provider select + api_key input + base_url input + model input）
  → 用户保存 → POST /api/v1/llm-config
  → 前端本地缓存 provider/model（不缓存 api_key）
```

---

## 7. 后端核心伪代码

### 7.1 chat_service.py — 文件IO与调用逻辑

```python
import json, uuid
from pathlib import Path
from backend.config import BASE_DIR
from backend.exceptions.handlers import AppException

SESSIONS_DIR = BASE_DIR / "sessions"
SESSIONS_DIR.mkdir(exist_ok=True)

def _session_path(user_id: int, session_id: str) -> Path:
    d = SESSIONS_DIR / str(user_id)
    d.mkdir(parents=True, exist_ok=True)
    p = (d / f"{session_id}.json").resolve()
    if not p.is_relative_to(SESSIONS_DIR.resolve()):
        raise AppException(code=4000, message="Invalid session id", status_code=400)
    return p

def load_messages(user_id: int, session_id: str) -> list[dict]:
    path = _session_path(user_id, session_id)
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))

def save_messages(user_id: int, session_id: str, messages: list[dict]) -> None:
    path = _session_path(user_id, session_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)  # 原子替换

def trim_messages(messages: list[dict], max_rounds: int) -> list[dict]:
    if max_rounds <= 0:
        return messages
    # 保留 system 消息（如果有）+ 最近 max_rounds*2 条消息
    system_msgs = [m for m in messages if m.get("role") == "system"]
    other_msgs = [m for m in messages if m.get("role") != "system"]
    keep = other_msgs[-max_rounds * 2:]
    return system_msgs + keep

async def stream_chat(
    user_id: int,
    session_id: str,
    content: str,
    config: dict,  # llm_config row
    max_rounds: int,
):
    messages = load_messages(user_id, session_id)
    messages.append({"role": "user", "content": content})

    # 构造请求体（OpenAI-compatible）
    req_messages = trim_messages(messages, max_rounds)
    # ... httpx.AsyncClient stream POST to config.base_url /chat/completions
    # yield SSE events
    # 收集完整回复
    full_reply = "..."
    messages.append({"role": "assistant", "content": full_reply})
    messages = trim_messages(messages, max_rounds)
    save_messages(user_id, session_id, messages)
```

### 7.2 chat.py — SSE 路由

```python
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.middleware.auth import get_current_user
from backend.models.user import User
from backend.services.chat_service import stream_chat, load_messages
from backend.utils.response import ok, fail
from backend.utils.logger import get_logger

logger = get_logger("routers.chat")
router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

@router.get("/messages/{session_id}")
def get_messages(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    messages = load_messages(current_user.id, session_id)
    return ok(data={"session_id": session_id, "messages": messages})

@router.post("/messages/{session_id}")
async def post_message(
    session_id: str,
    body: ChatMessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 校验 session 归属
    session_meta = db.query(ChatSession).filter_by(session_id=session_id, user_id=current_user.id).first()
    if not session_meta:
        raise AppException(code=4004, message="Session not found", status_code=404)

    # 读取用户 LLM 配置
    llm_config = db.query(LLMConfig).filter_by(user_id=current_user.id).first()
    if not llm_config:
        raise AppException(code=4000, message="LLM config not set", status_code=400)

    max_rounds = current_user.max_rounds or 0

    async def event_generator():
        try:
            yield f"event: message\ndata: {json.dumps({'type':'start'})}\n\n"
            full_content = ""
            async for delta in stream_chat(...):
                full_content += delta
                yield f"event: message\ndata: {json.dumps({'type':'delta','content':delta})}\n\n"
            yield f"event: message\ndata: {json.dumps({'type':'finish','content':full_content})}\n\n"
        except Exception as e:
            logger.exception("Chat stream error")
            yield f"event: message\ndata: {json.dumps({'type':'error','message':str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
```

---

## 8. 前端核心设计

### 8.1 状态管理（chat.js Pinia Store）

```javascript
export const useChatStore = defineStore('chat', () => {
  const sessions = ref([])
  const currentSessionId = ref(null)
  const messages = ref([])
  const config = ref(null)
  const streaming = ref(false)
  const error = ref(null)

  async function fetchSessions() { ... }
  async function createSession(title) { ... }
  async function switchSession(sessionId) { ... }
  async function deleteSession(sessionId) { ... }
  async function sendMessage(content) {
    // 乐观更新 user 消息
    // 建立 EventSource 或 fetch + ReadableStream 读取 SSE
    // 逐 delta 更新 assistant 消息
  }
  async function fetchConfig() { ... }
  async function saveConfig(cfg) { ... }

  return { sessions, currentSessionId, messages, config, streaming, error, ... }
})
```

### 8.2 SSE 读取方案

由于 Axios 对 EventSource 支持不佳，聊天发送使用原生 `fetch` + `ReadableStream`：

```javascript
const response = await fetch('/api/v1/chat/messages/' + sessionId, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer ' + localStorage.getItem('access_token'),
  },
  body: JSON.stringify({ content }),
})
const reader = response.body.getReader()
const decoder = new TextDecoder()
while (true) {
  const { done, value } = await reader.read()
  if (done) break
  const chunk = decoder.decode(value, { stream: true })
  // 解析 SSE 格式，提取 data: {...}
}
```

### 8.3 UI 布局

`Chat.vue` 采用左右布局：
- **左侧 `ChatSidebar`**：宽度 260px，会话列表（点击切换、长按/悬停显示删除）、底部"新建会话"按钮。
- **右侧主区域**：顶部 `ChatConfigPanel`（可折叠，显示当前配置摘要+设置按钮），中间 `ChatMessageList`（flex 反向滚动，用户消息右对齐/助手消息左对齐，Markdown 渲染），底部 `ChatInput`（textarea + 发送按钮）。

样式完全复用现有 CSS 变量：
- 卡片背景：`var(--bg-card)`
- 圆角：`var(--radius)`
- 按钮：`.btn`、`.btn-primary`
- 阴影：`var(--elevation-1)` ~ `var(--elevation-3)`

---

## 9. RAG 扩展预留方案

为后续接入 Chroma 向量检索预留以下扩展点，当前实现不启用，但接口和数据流兼容：

1. **system prompt 预留槽位**：JSON 消息数组首位固定保留 `{"role":"system","content":"..."}`，后续 RAG 检索到相关文档片段后，可动态改写 system prompt 或插入 `user` 消息前的 `context` 消息。

2. **chat_service.stream_chat 预留参数**：
   ```python
   async def stream_chat(..., rag_context: list[dict] | None = None):
       if rag_context:
           # 在 user 消息后、API 调用前，注入检索到的上下文
           req_messages = build_rag_messages(messages, rag_context)
   ```

3. **新增路由预留**：后续可新增 `POST /api/v1/chat/messages/{session_id}/rag`，与现有普通聊天路由并存，RAG 版本先走 Chroma 检索再调用 LLM。

4. **文件目录预留**：`sessions/{user_id}/` 目录与向量库文档切片天然一一对应，后续可基于 `session_id` 或 `document_id` 做关联检索。

---

## 10. 安全审查结论

### 10.1 已识别的风险与加固措施

| 风险项 | 等级 | 加固措施 |
|--------|------|---------|
| **跨用户会话访问** | 高 | 所有接口强制 `get_current_user`，文件路径拼接 `user_id`，`session_id` 校验归属。 |
| **目录遍历** | 高 | `_session_path()` 使用 `resolve()` + `is_relative_to()` 校验，与现有 `file_service` 相同逻辑。 |
| **API Key 泄露** | 高 | 数据库中加密存储（fernet），返回前端时脱敏，日志中绝不打印。 |
| **SSRF（外部API调用）** | 中 | `base_url` 校验合法 URL 格式，限制只允许已知域名白名单（siliconflow.cn, deepseek.com/api 等）。 |
| **Prompt 注入** | 中 | 不对用户输入做内容过滤（属于功能限制），但记录审计日志。系统 prompt 固定，不被用户覆盖。 |
| **无限流导致资源耗尽** | 中 | SSE 接口设置 `MAX_CHAT_TIMEOUT=120s`；单用户并发流式请求限制为 1（内存锁或 Redis 分布式锁）。 |
| **JSON 文件并发写冲突** | 中 | 使用 `.tmp` + `replace()` 原子写；单用户单会话的并发请求天然串行（由 FastAPI 单线程事件循环保证，若后续部署多 worker 需加文件锁）。 |
| **消息过长** | 低 | 单条消息限制长度 8000 字符（前端+后端双重校验）。 |
| **速率限制** | 低 | 新增 `/api/v1/chat/messages/*` 限流规则：每 IP 每分钟 30 次（可在 `main.py` RateLimitMiddleware 中配置）。 |

### 10.2 API Key 存储策略

采用对称加密（Fernet）存储：
- 密钥派生：`FERNET_KEY = SHA256(JWT_SECRET_KEY + "llm-config-salt")[:32]`，base64 编码为 Fernet key。
- 加密时机：写入 `llm_configs.api_key` 前加密。
- 解密时机：调用外部 LLM API 前解密到内存，用后立即 GC。
- 优势：不引入额外环境变量，利用现有 `JWT_SECRET_KEY`；即使数据库泄露，api_key 不可直接读取。

---

## 11. 环境变量与依赖变更

### 11.1 新增环境变量（`.env` / `config.py`）

| 变量名 | 必填 | 默认值 | 说明 |
|--------|------|--------|------|
| `CHAT_MAX_TIMEOUT` | 否 | `120` | 单次聊天流式调用最大超时（秒） |
| `CHAT_MAX_MESSAGE_LENGTH` | 否 | `8000` | 单条用户消息最大字符数 |
| `CHAT_RATE_LIMIT_PER_MINUTE` | 否 | `30` | 每 IP 每分钟聊天请求上限 |

### 11.2 新增 Python 依赖

添加到 `requirements.txt`：

```
httpx>=0.27,<1.0           # 异步 HTTP 客户端（流式调用 LLM）
openai>=1.30,<2.0          # OpenAI-compatible SDK（硅基流动/DeepSeek 均兼容）
cryptography>=42.0,<43.0   # Fernet 加密 api_key
```

> `httpx` 测试依赖中已有，但生产代码中需要显式声明。

### 11.3 前端依赖

无需新增。`marked` 已用于 Markdown 渲染（Reader.vue），可直接复用。

---

## 12. DevOps / 部署变更

### 12.1 nginx.conf 调整

SSE 接口需要禁用 buffering、延长超时：

```nginx
location /api/v1/chat/messages/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

    # SSE critical settings
    proxy_buffering off;
    proxy_cache off;
    proxy_read_timeout 300s;
    proxy_send_timeout 300s;
}
```

### 12.2 run.sh

无需修改。`sessions/` 目录由应用在运行时自动创建（与 `data/`、`storage/` 同级）。

### 12.3 目录权限

确保 `sessions/` 目录与 `storage/` 同权限（由运行用户读写）。

---

## 13. 回滚策略

### 13.1 数据库回滚

```bash
alembic downgrade 006
```

`downgrade()` 会删除 `llm_configs`、`chat_sessions` 表及 `users.max_rounds` 列。

### 13.2 代码回滚

```bash
git revert <合并提交>
# 或直接丢弃 feature/llm-chat 分支
```

### 13.3 数据保留策略

回滚前可选择性备份 `sessions/` 目录：
```bash
cp -r sessions sessions_backup_$(date +%Y%m%d)
```

### 13.4 兼容保障

- 新增路由独立，不影响现有 `/api/v1/documents`、`/api/v1/auth` 等。
- 前端新增 `/chat` 路由，旧路由表不变，不存在破坏性变更。
- `users.max_rounds` 有默认值 10，旧用户无感升级。

---

## 14. 测试策略

| 测试类型 | 覆盖点 | 目标覆盖率 |
|----------|--------|-----------|
| 单元测试 | `chat_service.py`：文件IO、消息裁剪、路径安全 | 90%+ |
| 单元测试 | `LLMConfig` / `ChatSession` schemas 校验 | 90%+ |
| 集成测试 | `POST /llm-config` CRUD | 80%+ |
| 集成测试 | `POST /chat-sessions` CRUD | 80%+ |
| 集成测试 | `POST /chat/messages/{id}` 流式响应（mock LLM API） | 80%+ |
| 集成测试 | 跨用户访问拦截 | 必须 100% |
| 集成测试 | 目录遍历防护 | 必须 100% |
| E2E | 前端：创建会话 → 发送消息 → 查看历史 | 关键路径 |

---

## 15. 阶段化实施建议（与 Git 规范对齐）

| 阶段 | 分支 | 内容 | 验证方式 |
|------|------|------|---------|
| Stage 1 | `feature/stage1-core` | 后端：数据库迁移、LLMConfig/ChatSession 路由、chat_service 文件IO、SSE 聊天接口 | cURL 测试所有 API；pytest 覆盖率 80%+ |
| Stage 2 | `feature/stage2-ui` | 前端：Chat.vue 页面、Sidebar、MessageList、Input、API 配置面板 | 浏览器手工验证；E2E 录制 |
| Stage 3 | `feature/stage3-settings` | 前端：SettingsModal 增加 max_rounds；后端：profile 扩展 | 浏览器验证 slider 与持久化 |
| Stage 4 | `feature/stage4-polish` | 安全加固（api_key 加密、限流、SSRF 白名单）、测试补全、nginx 配置 | 安全评审通过；全量测试通过 |

---

*方案制定：系统架构师（Team Lead 汇总）*
*评审参与：后端工程师、前端工程师、DevOps工程师、安全工程师*
