# BoKe LLM Chat 开发断点文档

> 日期：2026-05-07 18:05
> 状态：Stage 1 已完成，Stage 2 前端代码已写但未构建验证，Stage 3/4 待开发

---

## 一、分支状态

| 分支 | 当前状态 | 说明 |
|------|---------|------|
| `main` | acdab82 | 原始基线，未合并任何 LLM Chat 代码 |
| `feature/stage1-core` | 9de892e | Stage 1 后端完成（已 push 到 origin） |
| `feature/stage2-ui` | 881e28e | Stage 2 前端进行中（本地，未 push） |

**当前工作分支**：`feature/stage2-ui`

---

## 二、已完成内容

### Stage 1 — 后端核心（✅ 已完成，已 push）

**提交记录**：
1. `8e602ea` — 迁移、模型、schemas、路由、chat_storage
2. `fc2dbd7` — SSE 聊天接口、llm_client、chat_service
3. `9de892e` — RateLimitMiddleware 前缀匹配修复

**新增/修改文件**：
- `alembic/versions/007_add_llm_chat.py` — 迁移（llm_configs、chat_sessions、users.max_rounds）
- `backend/models/llm_config.py` — LLMConfig 模型
- `backend/models/chat_session.py` — ChatSession 模型
- `backend/models/user.py` — 新增 max_rounds 字段及关系
- `backend/models/__init__.py` — 导出新模型
- `backend/schemas/llm_config.py` — LLMConfigCreate / LLMConfigOut
- `backend/schemas/chat.py` — ChatSessionCreate/Update/Out, ChatMessageCreate, ChatMessagesOut
- `backend/schemas/user.py` — ProfileUpdate/Out 增加 max_rounds
- `backend/routers/llm_config.py` — GET/POST/DELETE /api/v1/llm-config（Upsert，api_key 脱敏）
- `backend/routers/chat_sessions.py` — CRUD /api/v1/chat-sessions（删除时清理 JSON 文件）
- `backend/routers/chat.py` — GET/POST /api/v1/chat/messages/{session_id}（SSE 流式）
- `backend/services/chat_storage.py` — 文件锁、原子写、路径安全、消息裁剪
- `backend/services/llm_client.py` — httpx.AsyncClient.stream 调用 OpenAI-compatible API
- `backend/services/chat_service.py` — stream_chat_session 编排
- `backend/services/__init__.py` — 导出服务函数
- `backend/config.py` — 新增 CHAT_MAX_TIMEOUT、CHAT_MAX_MESSAGE_LENGTH、CHAT_RATE_LIMIT_PER_MINUTE
- `backend/main.py` — 注册 llm_config、chat_sessions 路由；RateLimitMiddleware 增加聊天限流
- `backend/middleware/rate_limit.py` — 修复前缀匹配逻辑（以 / 结尾的规则匹配子路径）
- `requirements.txt` — 新增 openai、sse-starlette、cryptography、filelock

**测试状态**：pytest 126 passed / 1 failed（预存的 test_documents.py::test_delete_queued_document_blocked）

---

### Stage 2 — 前端 UI（🟡 代码已写，待构建验证）

**当前未提交变更**（在 `feature/stage2-ui` 分支工作区）：

| 文件 | 状态 | 说明 |
|------|------|------|
| `frontend/src/router/index.js` | M | 新增 /chat 路由 |
| `frontend/src/components/AppNavbar.vue` | M | 桌面端和移动端抽屉新增 "AI对话" 入口 |
| `frontend/src/api/index.js` | M | 新增 llm-config、chat-sessions、chat-messages API 封装（含 SSE fetch） |
| `frontend/src/stores/chat.js` | A | Pinia chat store：会话管理、消息收发、配置管理 |
| `frontend/src/views/Chat.vue` | A | 聊天主页面，组合所有组件 |
| `frontend/src/components/chat/ChatSidebar.vue` | A | 会话侧边栏（列表、新建、重命名、删除） |
| `frontend/src/components/chat/ChatConfigPanel.vue` | A | API 配置面板（可折叠） |
| `frontend/src/components/chat/ChatMessageList.vue` | A | 消息列表（marked 渲染、用户右对齐/助手左对齐） |
| `frontend/src/components/chat/ChatInput.vue` | A | 底部输入框，Enter 发送 |
| `frontend/src/components/chat/ChatEmptyState.vue` | A | 空状态提示 |

**待完成**：
- [ ] `npm run build` 验证无编译错误
- [ ] 浏览器访问 /chat 手工验证
- [ ] git commit 并 push（用户要求仅本地分支，不 push 到 origin main）

---

## 三、待开发阶段

### Stage 3 — 设置集成（🔴 未开始）

任务：前后端 max_rounds 字段打通
- 后端：`backend/routers/profile.py` 处理 max_rounds 更新
- 前端：`SettingsModal.vue` 新增消息轮数上限 slider（0-30）
- 分支：`feature/stage3-settings`

### Stage 4 — 安全加固（🔴 未开始）

任务：AES-256-GCM 加密、SSRF 白名单、速率限制、文件权限
- `backend/utils/crypto_utils.py` — AES-256-GCM 加密/解密
- `backend/routers/llm_config.py` — POST 时加密 api_key，GET 时脱敏
- `backend/services/llm_client.py` — 调用前解密 api_key
- `backend/schemas/llm_config.py` — base_url 白名单校验
- `backend/services/chat_storage.py` — 确认目录权限 0o700/0o600
- 分支：`feature/stage4-polish`

### Stage 4 — 测试补全（🔴 未开始）

- `tests/services/test_chat_service.py`
- `tests/api/test_llm_config.py`
- `tests/api/test_chat_sessions.py`
- `tests/api/test_chat.py`
- `tests/utils/test_crypto_utils.py`
- 覆盖率目标 >= 80%

### Stage 4 — DevOps（🔴 未开始）

- `nginx.conf` — SSE location 配置（proxy_buffering off、超时 300s）
- `.env.example` — CHAT_MAX_TIMEOUT、CHAT_MAX_MESSAGE_LENGTH、CHAT_RATE_LIMIT_PER_MINUTE
- 验证 run.sh

### 最终评审（🔴 未开始）

- `docs/code_review_report.md`

---

## 四、技术决策记录

依据 `llm_chat_plan_review_consolidation.md`（v1.1 评审纪要）：

| 决策 | 当前实现状态 |
|------|-------------|
| `users.max_rounds`（非 llm_configs.max_rounds） | ✅ 已落地（迁移 007 + user.py + schemas） |
| AES-256-GCM 加密（非 Fernet） | ⏳ Stage 4 实现 |
| 用户级配置（数据库存储 + 加密） | ✅ 表结构已就绪，加密待 Stage 4 |
| 速率限制 20 次/分钟/用户，SSE 并发 2 | ✅ main.py 规则已配置 |
| SSE 采用 `sse-starlette` | ✅ chat.py 已使用 EventSourceResponse |
| 服务拆分：chat_storage + chat_service + llm_client | ✅ 已拆分 |
| 原子写 + filelock | ✅ chat_storage.py 已实现 |
| Base URL 白名单 | ⏳ Stage 4 实现 |

---

## 五、回滚策略

数据库回滚：
```bash
alembic downgrade 006
```

代码回滚：
```bash
git checkout main
# 或删除本地分支
git branch -D feature/stage1-core feature/stage2-ui
```

数据备份：
```bash
cp -r sessions sessions_backup_$(date +%Y%m%d)
```

---

## 六、断点恢复指南

从本断点继续开发时：

1. **恢复工作区**：
   ```bash
   git checkout feature/stage2-ui
   ```

2. **完成 Stage 2**：
   ```bash
   cd frontend && npm run build
   # 修复构建错误后
   git add . && git commit -m "feat: Stage 2 前端聊天界面"
   ```

3. **创建 Stage 3 分支**：
   ```bash
   git checkout -b feature/stage3-settings
   ```

4. **按执行计划继续 A4 → A5 → A6 → A7 → A8**

---

*断点保存时间：2026-05-07 18:05*
*对应方案：docs/llm_chat_implementation_plan_v1.md + docs/llm_chat_plan_review_consolidation.md*
