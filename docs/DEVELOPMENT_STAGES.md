# BoKe 开发阶段规划

> 本文件保存完整的多阶段开发指令，供后续迭代引用。

## 阶段总览

| 阶段 | 标题 | 状态 |
|------|------|------|
| A | 稳住契约和状态模型 | ✅ 已完成 |
| B | 前端视觉与交互重构 | ✅ 已完成 |
| C | 后端异步化（入队 + worker + 状态轮询） | ✅ 已完成 |
| D | 可观测性与回归测试 | ✅ 已完成 |
| E-P0 | 收藏与书签 + 首页仪表盘 | 🔄 进行中 |
| E-P1 | 分类与标签 + 高级搜索 + 用户设置 | 待开始 |
| E-P2 | 批量操作 + 版本管理 + 审计日志 | 待开始 |
| E-P3 | Milvus + LLM + 分享/通知 + S3 + 限流优化 | 待开始 |

---

## 阶段 E-P0：收藏与书签 + 首页仪表盘

### E-P0-1 收藏（强烈建议先做）

- DB：documents 增加 is_favorite 布尔字段 + 索引
- API：PATCH /api/v1/documents/{doc_id}/favorite 切换收藏
- 前端：Documents.vue 星标按钮 + "仅收藏"筛选；新增 Favorites.vue
- 验收：收藏/取消收藏立即生效，列表筛选可用

### E-P0-2 首页仪表盘（次优先）

- DB：新增 activity_log 表记录查看、上传等操作；documents 增加 view_count、last_viewed_at
- API：/api/v1/dashboard/stats、recent、top、activity
- 前端：Dashboard.vue 作为登录后首页，包含 RecentDocs/TopDocs/StatsCard
- 验收：首页可展示最近访问/统计，查看文档会更新计数

---

## 阶段 E-P1：分类与标签 + 高级搜索 + 用户设置

- 分类/标签：categories（支持父子嵌套）、tags（用户级唯一）、document_tags 关联表；documents 增加 category_id
- 高级搜索：扩展搜索 API 支持日期范围、文件大小范围、分类、标签、文件类型等组合筛选；前端 AdvancedSearch.vue 面板
- 用户设置：user_settings 表存储主题、语言、默认排序、每页数量等；API 获取/更新设置；前端设置页面，支持切换浅色/深色主题（CSS 变量配合），即时生效并记住

---

## 阶段 E-P2：批量操作 + 版本管理 + 审计日志

- 批量：POST /api/v1/documents/batch/delete、/batch/category、/batch/tag、/batch/favorite；前端多选模式与批量工具栏
- 版本：document_versions 表，重新上传时保存旧版本；提供版本列表和回滚接口
- 审计：audit_log + 中间件自动记录敏感操作

---

## 阶段 E-P3：Milvus + LLM + 分享/通知 + S3 + 限流优化

- Milvus：embedding_service + vector_service + 降级到 FTS
- LLM：summary + RAG QA + SSE 流式（限流）
- 分享：share_token + 过期/次数限制
- 通知：WebSocket/SSE/Webhook（HMAC）
- S3：StorageBackend 抽象，LocalStorage/S3Storage
- 限流：Redis 后端滑窗/令牌桶 + Retry-After

---

## 全局工程约束

1. 统一返回结构：`{ "code": 0, "message": "ok", "data": {} }`
2. user_id 绑定与鉴权：所有数据绑定 user_id，禁止跨用户访问
3. 文件存储路径：`/storage/{user_id}/original|processed|thumbnails/`，所有文件访问必须经后端鉴权
4. 数据库迁移必须用 Alembic（含 downgrade 回滚路径）
5. 渐进式演进：先引入队列但保留同步 fallback，再切换默认入队
6. 文档状态机：queued -> processing -> ready / error
7. 日志 INFO/ERROR/DEBUG 分级，环境变量控制
8. 限流机制必须保留

## Git 规范

- 分支：feature/*, fix/*, refactor/*
- 提交：feat:, fix:, refactor:, docs:, chore:, test:
- 流程：从 main 创建分支 -> 开发 -> commit -> push -> PR -> 合并

## 多智能体协作机制

每阶段必须：
1. 架构师设计
2. 多角色评审（通过/不通过 + 理由）
3. 架构师裁定
4. 执行开发
5. 验证方式（cURL/前端操作/测试脚本）
6. Git 提交 + PR

## 角色定义

1. **系统架构师** - 设计改造方案、数据模型变更、API 契约
2. **后端工程师** - 实现改造和新增接口
3. **前端工程师** - 视觉与交互重构、新功能页面
4. **DevOps 工程师** - 运行环境配置、部署说明
5. **安全工程师** - 安全审查
6. **可观测性与测试负责人** - 日志、测试、CI
