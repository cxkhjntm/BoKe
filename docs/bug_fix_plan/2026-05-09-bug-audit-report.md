# BoKe 项目全面排查报告

**生成日期**: 2026-05-09
**分析范围**: 后端全部 Python 代码、前端全部 Vue/JS 代码、数据库模型与迁移、文件存储、聊天系统
**分析方式**: 5 个并行探索代理 + 直接代码审查
**总计发现**: 约 60+ 个问题，按优先级分为 4 级

---

## P0 — 严重 Bug（会导致功能不可用或数据丢失）

### 1. `/categories` 路由永远无法访问（死代码）
**文件**: `backend/routers/documents.py:241` vs `357-360`
**问题**: `GET /{doc_id}` 路由定义在 `GET /categories` 之前。FastAPI 按声明顺序匹配路由，请求 `GET /api/v1/documents/categories` 时，`/{doc_id}` 先匹配，尝试将 `"categories"` 解析为 `int` 失败，返回 422。`/categories` 端点永远不会被执行。
**修复**: 将 `GET /categories` 移到 `GET /{doc_id}` 之前。

### 2. 文本提取失败时文档仍被标记为 "ready"
**文件**: `backend/services/processing_service.py:50-58`
**问题**: 只有当文本提取和缩略图生成**都失败**时才标记为 `error`。如果缩略图成功但文本提取失败（加密PDF、损坏DOCX），文档被标记为 `ready` 但 `content_text=None`。后果：
- FTS5 搜索找不到该文档
- RAG 索引跳过它
- 用户看到文档 "ready" 但实际上功能不完整
**修复**: 对文本类文件（pdf/docx/md），只有 `text_ok=True` 时才标记 `ready`。

### 3. 文件上传后 DB 写入失败导致孤立文件
**文件**: `backend/routers/documents.py:132-143`
**问题**: `file_service.save_file()` 先将文件写入磁盘（line 132），然后 `document_service.create_document()` 创建 DB 记录（line 135）。如果 DB 写入失败（约束冲突、磁盘满），文件已保存到磁盘但没有对应 DB 记录，永远不会被清理。
**修复**: 用 try/except 包装，DB 失败时删除已保存的文件。

### 4. 删除文档时先删文件后提交 DB
**文件**: `backend/services/document_service.py:119-129`
**问题**: 删除顺序：先删物理文件（lines 122-126），再 `db.delete(doc)` + `db.commit()`（lines 128-129）。如果 commit 失败，物理文件已删除但 DB 记录仍然存在。用户看到文档列表里有记录，但下载时 404。
**修复**: 反转顺序 — 先删除 DB 记录（在事务中），成功后再删物理文件。

### 5. `chat_storage.load_messages` 未捕获 JSON 解析异常
**文件**: `backend/services/chat_storage.py:28`
**问题**: `json.loads(path.read_text(...))` — 如果 JSON 文件损坏（服务器崩溃导致写入中断），会抛出 `JSONDecodeError`，导致聊天端点 500 错误。
**修复**: 用 try/except 包装，解析失败时返回空列表 `[]`。

---

## P1 — 高优先级（影响用户体验或数据一致性）

### 6. 设置面板三个滑块共享同一个防抖计时器
**文件**: `frontend/src/components/SettingsModal.vue:138, 201-235`
**问题**: `saveTimer` 被 `onIntervalChange`、`onOpacityChange`、`onMaxRoundsChange` 共享。快速调整两个不同滑块时，前一个滑块的保存会被取消，更改丢失。
**修复**: 每个滑块使用独立的防抖计时器。

### 7. localStorage 损毁导致整个应用崩溃
**文件**: `frontend/src/stores/auth.js:8, 24`
**问题**: `JSON.parse(localStorage.getItem('user_profile') || 'null')` 和 `JSON.parse(localStorage.getItem('user_backgrounds') || '[]')` 在 store 初始化时执行。如果 localStorage 包含损坏的 JSON，会抛出 `SyntaxError`，导致应用在加载时崩溃，无法恢复。
**修复**: 用 try/catch 包装。

### 8. 聊天流式响应无取消机制
**文件**: `frontend/src/stores/chat.js:88-113`
**问题**: `sendMessage` 使用 `fetch` + SSE 流但没有 `AbortController`。用户在流式传输期间导航离开页面时，fetch 继续运行，SSE 回调继续更新已分离的响应式对象，浪费带宽。
**修复**: 添加 `AbortController`，在 `Chat.vue` 的 `onBeforeUnmount` 中取消。

### 9. Documents.vue 缩略图使用过期 token
**文件**: `frontend/src/views/Documents.vue:260`
**问题**: `const authToken = computed(() => localStorage.getItem('access_token') || '')` 直接读 localStorage，不响应 token 刷新。当 axios 拦截器刷新 token 后，缩略图 URL 仍使用旧 token，导致加载失败。
**修复**: 使用 `useAuthStore().accessToken` 替代 `localStorage.getItem`。

### 10. 聊天中孤立的用户消息（LLM 失败时）
**文件**: `backend/services/chat_service.py:65-101`
**问题**: 用户消息在 line 69 立即保存到文件。如果 LLM 流在 lines 90-94 失败（网络错误、API key 过期），没有助手回复被追加。会话文件中留下一个没有对应助手回复的用户消息。下次请求时，`trim_messages` 会将这个孤立消息包含在上下文中，导致 LLM 收到不平衡的对话。
**修复**: LLM 失败时，要么移除孤立的用户消息，要么追加一个错误提示的助手消息。

### 11. 没有 token 计数 — 可能超出 LLM 上下文限制
**文件**: `backend/services/chat_storage.py:51-57`
**问题**: `trim_messages` 只按消息数量限制（`max_rounds * 2`），没有 token 计数。如果 `max_rounds=10` 且每条消息平均 4000 字符（约 1000 token），总上下文可达约 40,000 token，超出许多 LLM 的上下文窗口。
**修复**: 添加 token 计数或字符数限制。

### 12. 重试/重新处理文档时缩略图文件泄漏
**文件**: `backend/services/document_service.py:155-156, 181-182`
**问题**: `retry_document` 和 `reprocess_document` 都将 `doc.thumbnail_path = None` 但没有调用 `file_service.delete_file()` 删除旧缩略图。旧缩略图文件永久孤立在磁盘上。
**修复**: 设置为 None 之前先删除旧文件。

### 13. Reader.vue 的 DOMPurify 配置导致图片错误回退失效
**文件**: `frontend/src/views/Reader.vue:192-195, 221, 225`
**问题**: `renderDocxContent` 注入带 `onerror` 处理器的 `<img>` 标签。但 DOMPurify 总是剥离 `on*` 事件处理器属性，`ADD_ATTR: ['onerror']` 配置无效。结果：加载失败的 DOCX 图片显示破碎图标而非预期的 "图片加载失败" 文字。
**修复**: 使用 CSS 方案或 `v-on:error` 处理器替代内联 `onerror`。

### 14. `file_service.delete_file` 缺少路径遍历检查
**文件**: `backend/services/file_service.py:38-43`
**问题**: `delete_file()` 直接拼接 `STORAGE_PATH / relative_path` 然后调用 `unlink()`，没有像 `get_file_path()` 和 `save_file()` 那样做 `is_relative_to` 检查。如果 DB 中的 `file_path` 被篡改（虽然后端使用 ORM 比较安全），可能删除任意文件。
**修复**: 添加与 `get_file_path` 相同的路径遍历检查。

---

## P2 — 中优先级（边界情况或潜在风险）

### 15. `record_view` 的 view_count 增量存在竞态条件
**文件**: `backend/services/document_service.py:302-308`
**问题**: `doc.view_count = (doc.view_count or 0) + 1` 是非原子的读-改-写操作。两个并发请求可能读到相同值，各自 +1 后写回，丢失一次计数。
**修复**: 使用 SQLAlchemy 表达式 `Document.view_count = Document.view_count + 1` 生成原子 SQL。

### 16. Document.user_id FK 缺少 ondelete CASCADE
**文件**: `backend/models/document.py:26`
**问题**: `ForeignKey("users.id")` 没有 `ondelete="CASCADE"`，而其他所有子模型都有。删除用户时文档记录会变成孤立数据。
**修复**: 添加 `ondelete="CASCADE"` 并创建新迁移。

### 17. LLMConfig.user_id 缺少数据库级唯一约束
**文件**: `backend/models/llm_config.py:14`
**问题**: `user_id` 没有 `unique=True`，但迁移 007 创建了唯一索引。模型和迁移不一致。竞态条件可能创建重复配置。
**修复**: 在模型中添加 `unique=True`。

### 18. 文件类型、浏览次数、最后浏览时间缺少索引
**文件**: `backend/models/document.py:29, 38, 39`
**问题**: `file_type`、`view_count`、`last_viewed_at` 在 `list_documents` 和 `dashboard_service` 中被查询和排序，但没有索引。
**修复**: 添加 `index=True` 并创建迁移。

### 19. 聊天会话删除顺序错误（先删 DB 后删文件）
**文件**: `backend/routers/chat_sessions.py:82-84`
**问题**: `db.delete(session)` + `db.commit()` 在 `delete_session_files()` 之前执行。如果文件删除失败，DB 记录已删除但会话文件仍留在磁盘上。
**修复**: 先删文件，再删 DB 记录。

### 20. Chat 会话的 `updated_at` 永远不会自动更新
**文件**: `backend/models/chat_session.py:19`
**问题**: `updated_at` 的 `onupdate` 只在 ORM 级别更新触发。但 `chat_service.py` 只修改文件中的消息，从不触碰 `ChatSession` DB 记录。会话列表按 `updated_at` 排序，但实际总是显示创建顺序。
**修复**: 在 `stream_chat_session` 中更新 `session.updated_at`。

### 21. `sendChatMessage` 绕过了 axios 拦截器
**文件**: `frontend/src/api/index.js:255-296`
**问题**: 使用原生 `fetch` 而非 axios，绕过了请求拦截器（自动附加 token）和响应拦截器（401 自动刷新）。token 过期时没有自动刷新或重定向。
**修复**: 添加手动 401 检查，或集成刷新逻辑。

### 22. 配置文件缺少数值范围验证
**文件**: `backend/config.py:44, 49, 63-68`
**问题**: `MAX_UPLOAD_SIZE_MB`、`RATE_LIMIT_LOGIN`、`CHAT_MAX_TIMEOUT` 等直接 `int()` 转换，无边界检查。设置为 0 或负数会导致异常行为。非整数环境变量会导致启动崩溃。
**修复**: 添加范围验证和 try/except。

### 23. RAG 配置缺少验证约束
**文件**: `backend/schemas/rag.py:26-31`
**问题**: `chunk_overlap >= chunk_size` 会导致文本分割器行为异常。`top_k=0` 不返回结果。`threshold_dist=-1` 过滤掉所有内容。
**修复**: 添加 Pydantic 验证器。

### 24. BackgroundReorder 允许空列表和重复 ID
**文件**: `backend/schemas/user.py:48-49`
**问题**: `background_ids: list[int]` 没有 `min_length` 或唯一性检查。空列表会清除所有位置值。重复 ID 会导致位置状态不一致。
**修复**: 添加 `min_length=1` 和唯一性验证。

### 25. 头像/背景上传：旧文件在新提交前被删除
**文件**: `backend/routers/profile.py:101-106, 131-137`
**问题**: 上传头像时：先删旧文件（line 101），再保存新文件（line 103），最后 DB 提交（line 105）。如果 DB 提交失败，新文件孤立且旧文件已丢失 — 用户头像完全丢失。
**修复**: 先保存新文件并提交 DB，成功后再删旧文件。

### 26. FTS5 触发器在迁移表重建时丢失
**文件**: `alembic/versions/002`, `003`, `006`
**问题**: 迁移 002/003/006 通过 `DROP TABLE documents; ALTER TABLE documents_new RENAME TO documents;` 重建表。SQLite 会自动删除被 drop 表上的触发器。这些迁移都没有重建 FTS5 触发器。
**缓解**: `main.py` 的 `_setup_fts5()` 在启动时用 `IF NOT EXISTS` 重建触发器。但独立运行 `alembic upgrade head` 时触发器会丢失。

### 27. 迁移 001 的 key_prefix 列大小不匹配
**文件**: `alembic/versions/001:60` vs `models/api_key.py:15`
**问题**: 迁移定义 `String(8)`，模型定义 `String(11)`。`generate_api_key()` 生成 11 字符前缀。SQLite 不强制字符串长度所以运行正常，但架构不一致。

---

## P3 — 低优先级（代码质量 / 非功能性）

### 28. 所有模型使用已弃用的 `datetime.utcnow()`
**文件**: 全部 10 个模型文件 + 多个 service 文件
**问题**: Python 3.12+ 已弃用 `datetime.utcnow()`（返回 naive datetime）。应使用 `datetime.now(timezone.utc)`。

### 29. 健康检查每次请求都执行磁盘写入
**文件**: `backend/routers/health.py:25-28`
**问题**: 每次健康检查都创建并删除文件。高频轮询时造成不必要的 I/O。
**修复**: 改用 `os.access(path, os.W_OK)` 检查。

### 30. API Key 每次请求都写 DB 更新 last_used_at
**文件**: `backend/middleware/auth.py:144-146`
**问题**: 每个 API key 认证的请求都触发 DB 写入。
**修复**: 批量更新（仅当 last_used_at 超过 1 分钟时更新）。

### 31. ChromaDB 全局单例非线程安全
**文件**: `backend/services/rag_service.py:33-37`
**问题**: `_get_chroma_client()` 的懒初始化没有锁保护。两个并发请求可能同时创建客户端。
**修复**: 使用 threading.Lock 保护初始化。

### 32. `formatSize` 不处理 null/undefined/负数
**文件**: `frontend/src/utils/format.js:6-10`
**问题**: `bytes` 为 null/undefined 时输出 `"NaN B"`。
**修复**: 添加守卫 `if (!bytes || bytes <= 0) return '0 B'`。

### 33. Documents.vue 的 setTimeout 未清理
**文件**: `frontend/src/views/Documents.vue:403, 409`
**问题**: 上传成功后的 `setTimeout` 没有在 `onBeforeUnmount` 中清理。
**修复**: 保存 timeout ID 并在卸载时清除。

### 34. ChatMessageList 只监听消息数量变化，不监听内容变化
**文件**: `frontend/src/components/chat/ChatMessageList.vue:73-79`
**问题**: 自动滚动的 watcher 只监听 `messages.length`。流式传输期间助手消息内容增长但数组长度不变，用户需要手动滚动查看新内容。
**修复**: 深度监听 `messages` 或使用 `MutationObserver`。

### 35. 聊天 store 的 `sendMessage` 出错时用户消息仍保留
**文件**: `frontend/src/stores/chat.js:94, 106-109`
**问题**: 乐观添加的用户消息在服务器错误时不会被移除。用户看到自己的消息但没有回复。如果重试会发送重复消息。

### 36. 迁移 env.py 缺少模型导入
**文件**: `alembic/env.py:7`
**问题**: 缺少 `UserBackground`、`EmbeddingConfig`、`RAGConfig` 的导入。如果将来使用 Alembic autogenerate，这些表不会被检测到。

### 37. 多个迁移创建冗余索引
**文件**: `alembic/versions/007`, `008`
**问题**: 对同一列同时创建非唯一索引和唯一索引。唯一索引已包含非唯一索引的功能。

### 38. chat_service 的 `_fetch_rag_context` 在异步上下文中创建同步 DB session
**文件**: `backend/services/chat_service.py:16-54`
**问题**: 同步 `SessionLocal()` 在 async generator 中使用，可能违反 SQLAlchemy 的线程模型。

---

## 统计汇总

| 优先级 | 数量 | 关键问题 |
|--------|------|----------|
| **P0 严重** | 5 | 死路由、错误状态标记、文件孤立、JSON 解析崩溃 |
| **P1 高** | 9 | 滑块丢失、token 过期、聊天孤立消息、路径遍历、LLM 上下文溢出 |
| **P2 中** | 13 | 竞态条件、FK 缺失、索引缺失、配置验证、文件删除顺序 |
| **P3 低** | 11 | 弃用 API、性能优化、代码质量 |

**安全/鉴权相关**（按要求降低优先级）: #14 delete_file 路径遍历、#21 绕过 axios 拦截器、#22 配置验证 — 已包含在 P1/P2 中但严重性因个人使用场景而降低。

**建议优先修复顺序**: P0 #1 → #2 → #3 → #4 → #5，然后 P1 #6 → #7 → #10 → #11。
