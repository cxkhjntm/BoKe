# BoKe 大模型问答功能 — 下一步多智能体执行计划

> 制定日期：2026-05-07
> 对应方案：《功能实施方案 v1.0》存放于同目录 `llm_chat_implementation_plan_v1.md`

---

## 1. Agent 清单与分工

| 编号 | Agent 名称 | 类型 | 职责 | 对应方案章节 | 依赖前置 Agent |
|------|-----------|------|------|-------------|---------------|
| A1 | `backend-core-dev` | general-purpose | Stage 1 后端核心开发：数据库迁移、模型、schemas、LLMConfig 路由、ChatSession 路由、chat_service 文件 IO 与裁剪逻辑 | 第 4 章、第 5 章（5.1/5.2）、第 7 章 | 无 |
| A2 | `backend-chat-dev` | general-purpose | Stage 1 后端聊天接口：SSE 路由、httpx 流式调用 LLM、openai-compatible 集成 | 第 5 章（5.3）、第 7 章 | A1（依赖模型与 service 基础） |
| A3 | `frontend-dev` | general-purpose | Stage 2 前端开发：Chat.vue、ChatSidebar、ChatMessageList、ChatInput、ChatConfigPanel、router、api、store | 第 8 章 | A1（依赖 API 契约） |
| A4 | `settings-dev` | general-purpose | Stage 3 设置扩展：前后端 max_rounds 字段打通 | 第 5 章（5.4）、第 8 章（SettingsModal） | A1, A3 |
| A5 | `security-dev` | general-purpose | Stage 4 安全加固：api_key Fernet 加密、SSRF 白名单、速率限制、路径遍历双重校验 | 第 10 章 | A1, A2 |
| A6 | `test-dev` | general-purpose | 全阶段测试补全：pytest 单元/集成测试、覆盖率 80%+ | 第 14 章 | A1, A2 |
| A7 | `devops-dev` | general-purpose | Stage 4 DevOps：nginx SSE 配置、requirements.txt 更新、run.sh 验证 | 第 11 章、第 12 章 | A2（需确认 SSE 接口稳定） |
| A8 | `reviewer` | code-reviewer | 代码评审：所有提交前的 CRITICAL/HIGH 问题拦截 | 第 13 章（质量门） | 各阶段完成后 |

---

## 2. 执行顺序与并行策略

```
Week 1 (Stage 1 - Core Backend)
├── A1: backend-core-dev  ----------┐
│   (迁移 + 模型 + schemas +        │  可并行启动
│    LLMConfig/ChatSession 路由      │  但 A2 需等待 A1 完成基础结构
│    + chat_service 文件IO)         │
└── A2: backend-chat-dev  ----------+---> 依赖 A1
    (SSE 聊天接口 + openai 流式调用)

Week 2 (Stage 2 - Frontend)
├── A3: frontend-dev  --------------┐
│   (Chat.vue + 组件 + store +     │  依赖 A1/A2 API 就绪
│    router + api 封装)             │
└── A6: test-dev (集成测试骨架)      │  可与 A3 并行

Week 3 (Stage 3 - Settings)
├── A4: settings-dev  --------------┐
│   (profile max_rounds +           │  依赖 A1, A3
│    SettingsModal slider)          │
└── A6: test-dev (补全测试)          │  并行

Week 4 (Stage 4 - Security & DevOps)
├── A5: security-dev  --------------┐
│   (加密 + SSRF + 限流)            │  依赖 A1, A2
├── A7: devops-dev  ----------------┤  依赖 A2
│   (nginx + requirements)          │
└── A8: reviewer  ------------------┤  全阶段代码评审
    (最终质量门)                     │
```

---

## 3. 每个 Agent 的启动提示词

### A1 — backend-core-dev

```text
你是 BoKe 项目的后端开发工程师，负责实现大模型问答功能的后端核心基础结构（Stage 1）。

工作目录：/home/ubuntuuser/BoKe
方案文档：/home/ubuntuuser/BoKe/docs/llm_chat_implementation_plan_v1.md
对应章节：第 4 章（数据库变更）、第 5 章（5.1 LLMConfig、5.2 ChatSession）、第 7 章（chat_service 文件IO）

你需要完成：
1. 创建 Alembic 迁移 `alembic/versions/007_add_llm_chat.py`，包含 llm_configs 表、chat_sessions 表、users.max_rounds 字段。
2. 创建 backend/models/llm_config.py 和 backend/models/chat_session.py，并在 __init__.py 导出。
3. 创建 backend/schemas/llm_config.py 和 backend/schemas/chat.py，包含所有 Pydantic schemas（Create/Update/Out）。
4. 创建 backend/routers/llm_config.py，实现 GET / POST / DELETE /api/v1/llm-config（Upsert 语义）。
5. 创建 backend/routers/chat_sessions.py，实现 GET / POST / PATCH / DELETE /api/v1/chat-sessions。
6. 创建 backend/services/chat_service.py，实现：
   - _session_path(user_id, session_id) — 路径安全校验
   - load_messages(user_id, session_id)
   - save_messages(user_id, session_id, messages) — 原子写（.tmp + replace）
   - trim_messages(messages, max_rounds)
7. 修改 backend/main.py 注册新路由。

技术约束：
- 必须使用现有认证依赖 get_current_user
- 响应格式统一使用 ok() / fail()
- 所有查询必须带 user_id 过滤
- 路径校验必须使用 resolve() + is_relative_to()
- 代码风格与现有项目一致（单文件 <800 行，函数 <50 行）

完成后运行 pytest 确保现有测试不挂，提交到 feature/stage1-core 分支。
```

### A2 — backend-chat-dev

```text
你是 BoKe 项目的后端开发工程师，负责实现大模型问答的 SSE 流式聊天接口（Stage 1 后半段）。

工作目录：/home/ubuntuuser/BoKe
方案文档：/home/ubuntuuser/BoKe/docs/llm_chat_implementation_plan_v1.md
对应章节：第 5 章（5.3 chat.py）、第 7 章（stream_chat）
依赖前置：A1 已完成（模型、chat_service 基础结构就绪）

你需要完成：
1. 重写 backend/routers/chat.py：
   - GET /api/v1/chat/messages/{session_id} — 读取 JSON 文件消息历史
   - POST /api/v1/chat/messages/{session_id} — 流式 SSE 返回
2. 在 backend/services/chat_service.py 中实现 stream_chat()：
   - 使用 httpx.AsyncClient 流式调用外部 LLM（OpenAI-compatible 格式）
   - 支持硅基流动和 DeepSeek（通过 base_url + api_key 区分）
   - 边接收边 yield delta 字符串
   - 收集完整回复后追加到 JSON 文件并裁剪
3. 修改 backend/config.py 新增 CHAT_MAX_TIMEOUT、CHAT_MAX_MESSAGE_LENGTH。
4. 在 main.py 的 RateLimitMiddleware 中新增聊天接口限流规则。

技术约束：
- SSE 格式必须严格：event: message\ndata: {...}\n\n
- 异常时必须 yield error 事件后关闭流
- api_key 从 llm_configs 表读取（当前阶段可明文，A5 会加密）
- 单条消息长度校验

完成后提交到 feature/stage1-core 分支（与 A1 同分支）。
```

### A3 — frontend-dev

```text
你是 BoKe 项目的前端开发工程师，负责实现大模型问答页面（Stage 2）。

工作目录：/home/ubuntuuser/BoKe
方案文档：/home/ubuntuuser/BoKe/docs/llm_chat_implementation_plan_v1.md
对应章节：第 8 章（前端核心设计）
依赖前置：A1/A2 已完成，API 已就绪

你需要完成：
1. 修改 frontend/src/router/index.js，新增 /chat 路由（requiresAuth: true）。
2. 修改 frontend/src/components/AppNavbar.vue，新增"AI对话"导航入口（中英文均可）。
3. 修改 frontend/src/api/index.js，新增：
   - getLLMConfig / saveLLMConfig / deleteLLMConfig
   - getChatSessions / createChatSession / updateChatSession / deleteChatSession
   - getChatMessages / sendChatMessage（SSE fetch 封装）
4. 创建 frontend/src/stores/chat.js（Pinia），管理 sessions、currentSessionId、messages、config、streaming 状态。
5. 创建以下组件（全部使用现有 CSS 变量，保持风格一致）：
   - ChatSidebar.vue — 会话列表、新建、删除
   - ChatConfigPanel.vue — provider 选择、api_key、base_url、model 输入
   - ChatMessageList.vue — 消息渲染（复用 marked），用户右对齐/助手左对齐
   - ChatInput.vue — textarea + 发送按钮
6. 创建 frontend/src/views/Chat.vue，组合以上组件。

技术约束：
- 样式必须使用 var(--bg-card)、var(--primary)、var(--radius) 等现有变量
- 按钮使用 .btn / .btn-primary 类
- SSE 使用原生 fetch + ReadableStream（不用 Axios）
- 流式接收时更新 messages 数组需保持响应式
- 空数据、加载状态、异常状态必须处理

完成后提交到 feature/stage2-ui 分支。
```

### A4 — settings-dev

```text
你是 BoKe 项目的前后端开发工程师，负责实现消息轮数上限设置（Stage 3）。

工作目录：/home/ubuntuuser/BoKe
方案文档：/home/ubuntuuser/BoKe/docs/llm_chat_implementation_plan_v1.md
对应章节：第 5 章（5.4 profile.py）、第 8 章（SettingsModal）
依赖前置：A1（后端 max_rounds 字段已存在）、A3（前端基础已就绪）

你需要完成：
1. 后端：
   - 修改 backend/schemas/user.py，ProfileUpdate 增加 max_rounds: int | None = Field(None, ge=0, le=30)
   - 修改 backend/schemas/user.py，ProfileOut 增加 max_rounds: int = 10
   - 修改 backend/routers/profile.py，update_profile 处理 max_rounds 字段
   - 修改 backend/models/user.py，User 模型增加 max_rounds = Column(Integer, default=10)
2. 前端：
   - 修改 frontend/src/components/SettingsModal.vue，在轮播间隔 slider 下方新增"消息轮数上限" slider（0~30，0 表示无限制）
   - 修改 frontend/src/stores/auth.js，userProfile 同步 max_rounds
   - 修改 frontend/src/api/index.js，updateProfile 可传 max_rounds

技术约束：
- slider 样式复用现有 .slider CSS
- 保存逻辑复用现有 debounce（300ms）+ updateProfile 模式
- 后端默认值 10，旧用户无感升级

完成后提交到 feature/stage3-settings 分支。
```

### A5 — security-dev

```text
你是 BoKe 项目的安全工程师，负责大模型问答功能的安全加固（Stage 4）。

工作目录：/home/ubuntuuser/BoKe
方案文档：/home/ubuntuuser/BoKe/docs/llm_chat_implementation_plan_v1.md
对应章节：第 10 章（安全审查结论）
依赖前置：A1, A2 已完成基础代码

你需要完成：
1. API Key 加密存储：
   - 在 backend/utils/ 下新增 crypto_utils.py，基于 cryptography.fernet 实现 encrypt/decrypt
   - 密钥派生：SHA256(JWT_SECRET_KEY + "llm-config-salt")[:32]，base64 编码为 Fernet key
   - 修改 llm_config.py 的 POST / 路由：写入前加密 api_key
   - 修改 llm_config.py 的 GET / 路由：返回脱敏后的 api_key（前8位+***+后4位）
   - 修改 chat_service.stream_chat()：调用前解密 api_key 到内存
2. SSRF 防护：
   - 在 schemas/llm_config.py 中增加 base_url 校验：只允许 *.siliconflow.cn、*.deepseek.com/api 等已知域名
3. 速率限制：
   - 修改 backend/main.py，RateLimitMiddleware 规则增加 "/api/v1/chat/messages/": (30, 60)
4. 路径遍历双重校验：
   - 确认 chat_service._session_path() 已使用 resolve() + is_relative_to()
   - 增加单元测试验证非法 session_id 被拦截

技术约束：
- 不引入新的环境变量（复用 JWT_SECRET_KEY）
- 加密/解密必须单测覆盖
- 日志中不得出现明文 api_key

完成后提交到 feature/stage4-polish 分支。
```

### A6 — test-dev

```text
你是 BoKe 项目的测试工程师，负责补全大模型问答功能的测试套件。

工作目录：/home/ubuntuuser/BoKe
方案文档：/home/ubuntuuser/BoKe/docs/llm_chat_implementation_plan_v1.md
对应章节：第 14 章（测试策略）
依赖前置：各阶段功能代码已完成

你需要完成：
1. tests/services/test_chat_service.py：
   - 测试 load_messages / save_messages（正常、空文件、非法路径）
   - 测试 trim_messages（各种 max_rounds 边界）
   - 测试 _session_path 目录遍历防护
2. tests/api/test_llm_config.py：
   - CRUD 完整流程
   - 跨用户访问拦截（用户A不能操作用户B的配置）
   - 非法 provider / 非法 base_url 校验
3. tests/api/test_chat_sessions.py：
   - CRUD 完整流程
   - 删除会话同时删除 JSON 文件
   - 跨用户访问拦截
4. tests/api/test_chat.py：
   - GET messages 正常/空
   - POST messages SSE 响应格式（mock LLM API，使用 httpx MockTransport 或 respx）
   - 未配置 LLM 时的错误响应
   - 消息长度超限校验

技术约束：
- 复用现有 conftest.py 的 client、admin_user、auth_headers fixture
- 测试数据库隔离（function-scope db_session）
- 覆盖率目标：新代码 80%+

完成后随对应阶段分支提交或单独 test/ 分支提交。
```

### A7 — devops-dev

```text
你是 BoKe 项目的 DevOps 工程师，负责部署与环境配置更新（Stage 4）。

工作目录：/home/ubuntuuser/BoKe
方案文档：/home/ubuntuuser/BoKe/docs/llm_chat_implementation_plan_v1.md
对应章节：第 11 章（环境变量与依赖）、第 12 章（DevOps / 部署变更）
依赖前置：A2（SSE 接口稳定）

你需要完成：
1. 修改 requirements.txt：
   - 新增 httpx>=0.27,<1.0
   - 新增 openai>=1.30,<2.0
   - 新增 cryptography>=42.0,<43.0
2. 修改 nginx.conf：
   - 在现有 location /api/ 之前新增 location /api/v1/chat/messages/，配置 proxy_buffering off、proxy_cache off、proxy_read_timeout 300s
3. 验证 run.sh：
   - 确认启动后 sessions/ 目录自动创建（代码中已处理，无需脚本修改）
   - 确认 .env 中新增 CHAT_* 变量有默认值（config.py 已处理）
4. 更新 .env.example：
   - 新增 CHAT_MAX_TIMEOUT、CHAT_MAX_MESSAGE_LENGTH、CHAT_RATE_LIMIT_PER_MINUTE（带默认值注释）

完成后提交到 feature/stage4-polish 分支。
```

### A8 — reviewer

```text
你是 BoKe 项目的代码评审员，负责在所有开发阶段完成后进行最终质量评审。

工作目录：/home/ubuntuuser/BoKe
方案文档：/home/ubuntuuser/BoKe/docs/llm_chat_implementation_plan_v1.md
质量门标准：
- 无 CRITICAL 或 HIGH 安全问题
- 无跨用户数据访问漏洞
- 测试覆盖率 >= 80%
- 无硬编码密钥
- 函数 < 50 行，文件 < 800 行
- API 响应格式统一 {code, message, data}

评审范围：
- backend/models/llm_config.py
- backend/models/chat_session.py
- backend/routers/llm_config.py
- backend/routers/chat_sessions.py
- backend/routers/chat.py
- backend/services/chat_service.py
- frontend/src/views/Chat.vue
- frontend/src/stores/chat.js
- frontend/src/api/index.js（新增部分）
- tests/api/test_chat.py
- tests/api/test_llm_config.py
- tests/api/test_chat_sessions.py

输出评审报告到 /home/ubuntuuser/BoKe/docs/code_review_report.md，列出所有 CRITICAL/HIGH/MEDIUM/LOW 问题及修复建议。
```

---

## 4. 阶段提交规范（与 Git 规范对齐）

每个 Agent 完成阶段后必须：

```bash
git checkout -b feature/stageX-xxx
git add .
git commit -m "feat: 完成 Stage X — 简短描述" -m "详细说明：
- 实现了...
- 包含...
- 测试覆盖...
验证方式：详见 docs/stageX-test.md，pytest -q tests/"
git push -u origin feature/stageX-xxx
```

---

## 5. 风险应对与应急方案

| 风险 | 应对 |
|------|------|
| Agent 执行中遇到未预见的代码冲突 | 立即暂停，通知 Team Lead（我）进行人工裁决，必要时调整方案 v1.1 |
| 外部 LLM API（硅基流动/DeepSeek）接口变更 | chat_service 中封装统一调用层，变更时只需修改一处 |
| SSE 在生产环境 nginx 下不流式 | A7 已在 nginx 中关闭 buffering，若仍有问题启用 chunked_transfer_encoding on |
| JSON 文件在高并发下损坏 | 原子写（.tmp + replace）已覆盖；多 worker 场景下后续可加文件锁（fcntl） |
| Alembic 迁移失败 | 回滚到 006，检查 SQLite 版本兼容性，修复后重新生成迁移 |

---

*执行计划制定：系统架构师（Team Lead）*
*评审参与：全角色 Agent*
