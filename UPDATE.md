# BoKe 更新指南

本文档指导你将 BoKe 系统从旧版本更新到最新版本。涵盖代码拉取、依赖更新、数据库迁移、前端构建、服务重启等完整流程。

---

## 目录

- [更新前准备](#更新前准备)
- [快速更新（一键脚本）(#快速更新一键脚本)
- [手动更新（详细步骤）](#手动更新详细步骤)
- [版本间重大变更说明](#版本间重大变更说明)
- [更新后验证](#更新后验证)
- [回滚操作](#回滚操作)
- [常见问题排查](#常见问题排查)

---

## 更新前准备

### 1. 确认当前版本

```bash
cd ~/BoKe  # 进入项目目录
git log --oneline -5  # 查看最近5次提交
git describe --tags 2>/dev/null || echo "无标签版本"
```

记录当前版本号，以便更新失败时回滚。

### 2. 备份数据库

**强烈建议在更新前备份数据库！**

```bash
# 方法一：停止服务后备份（推荐，数据一致性最好）
sudo systemctl stop boke
sudo systemctl stop boke-celery 2>/dev/null || true
cp ~/BoKe/data/app.db ~/BoKe/data/app.db.backup.$(date +%Y%m%d_%H%M%S)
sudo systemctl start boke

# 方法二：在线备份（不停服）
cd ~/BoKe
source venv/bin/activate
python3 -c "
import sqlite3
from datetime import datetime
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
src = sqlite3.connect('data/app.db')
dst = sqlite3.connect(f'data/app.db.backup.{timestamp}')
src.backup(dst)
src.close()
dst.close()
print(f'备份完成: data/app.db.backup.{timestamp}')
"
```

### 3. 备份配置文件

```bash
cp ~/BoKe/.env ~/BoKe/.env.backup.$(date +%Y%m%d_%H%M%S)
```

### 4. 检查磁盘空间

```bash
df -h ~/BoKe
```

确保有足够的空间存放新代码、依赖和构建产物（建议至少 2GB 可用空间）。

---

## 快速更新（一键脚本）

项目根目录下提供了 `update.sh` 脚本，执行即可完成更新：

```bash
cd ~/BoKe
chmod +x update.sh
bash update.sh
```

> **脚本与手动步骤的对应关系：**
> 
> | 脚本阶段 | 对应手动步骤 | 说明 |
> |----------|-------------|------|
> | 阶段 1 | 步骤 1 | 停止服务 |
> | 阶段 2 | 步骤 2 | 备份数据库 |
> | 阶段 3 | 步骤 3 | 暂存本地修改 → 拉取代码 → 恢复修改 |
> | 阶段 4 | 步骤 4 | 更新 Python 依赖 |
> | 阶段 5 | 步骤 5 | 运行数据库迁移 |
> | 阶段 6 | 步骤 6 | 构建前端 |
> | 阶段 7 | 步骤 7+8 | 重载 systemd + 重启服务 |
> | 阶段 8 | 步骤 9 | 验证服务状态 |
> 
> **如果脚本中途失败，错误信息会提示从哪个手动步骤继续操作。**
> 
> **如果 `git stash pop` 产生冲突，脚本会停止并提示从手动步骤 3 继续。**

---

## 手动更新（详细步骤）

如果需要更精细的控制，或一键脚本执行失败，请按以下步骤手动操作。

### 步骤 1：停止服务

```bash
# 停止后端服务
sudo systemctl stop boke

# 停止 Celery Worker（如果配置了）
sudo systemctl stop boke-celery 2>/dev/null || true

# 验证服务已停止
sudo systemctl status boke
sudo systemctl status boke-celery 2>/dev/null || true
```

### 步骤 2：备份数据库

```bash
cd ~/BoKe
cp data/app.db data/app.db.backup.$(date +%Y%m%d_%H%M%S)
ls -la data/app.db.backup.*
```

确认备份文件已生成且大小不为 0。

### 步骤 3：拉取最新代码

```bash
cd ~/BoKe

# 查看当前版本
echo "当前版本:"
git log --oneline -1

# 暂存本地修改（如果有）
git stash push -m "本地临时修改"

# 拉取更新
git fetch origin
git pull origin main

# 恢复本地修改
git stash pop 2>/dev/null || echo "没有暂存的本地修改"

# 查看更新后的版本
echo "更新后版本:"
git log --oneline -1

# 查看本次更新包含的变更
echo "本次更新内容:"
git log --oneline origin/main~10..origin/main
```

> **注意：** 如果 `git stash pop` 产生冲突，需要手动解决冲突后继续。

### 步骤 4：更新 Python 依赖

```bash
cd ~/BoKe

# 激活虚拟环境
source venv/bin/activate

# 更新依赖
pip install -r requirements.txt

# 如果使用国内镜像源
# pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 验证关键依赖
python -c "import fastapi; print('FastAPI', fastapi.__version__)"
python -c "import sqlalchemy; print('SQLAlchemy', sqlalchemy.__version__)"
python -c "import alembic; print('Alembic OK')"
```

### 步骤 5：运行数据库迁移

```bash
cd ~/BoKe

# 确保虚拟环境已激活
source venv/bin/activate

# 加载环境变量
set -a
source .env
set +a

# 查看待执行的迁移
alembic history

# 执行迁移
alembic upgrade head

# 验证迁移结果
alembic current
```

**预期输出示例：**
```
INFO  [alembic] Running upgrade 008 -> 5b0d2d3e48aa, support_multiple_llm_configs
```

如果迁移失败，请参见[常见问题排查](#常见问题排查)。

### 步骤 6：构建前端

```bash
cd ~/BoKe/frontend

# 清理旧的构建产物（可选，解决缓存问题）
rm -rf dist node_modules

# 安装依赖
npm install

# 如果 npm 速度慢，使用淘宝镜像
# npm config set registry https://registry.npmmirror.com
# npm install

# 构建
npm run build

# 验证构建产物
ls -la dist/
ls -la dist/assets/
```

**预期输出：** `dist/` 目录下应有 `index.html`，`assets/` 目录下应有 `.js` 和 `.css` 文件。

```bash
cd ~/BoKe
```

### 步骤 7：重载 Systemd 配置（如果 service 文件有变更）

```bash
sudo systemctl daemon-reload
```

### 步骤 8：重启服务

```bash
# 重启后端
sudo systemctl start boke

# 重启 Celery Worker（如果配置了）
sudo systemctl start boke-celery 2>/dev/null || true

# 重载 Nginx（如果配置文件有变更）
sudo systemctl reload nginx
```

### 步骤 9：验证服务状态

```bash
# 检查服务状态
sudo systemctl status boke
sudo systemctl status boke-celery 2>/dev/null || true
sudo systemctl status nginx

# 测试健康检查
curl -s http://localhost:8000/api/v1/health

# 查看实时日志
sudo journalctl -u boke -f
```

**预期输出：**
- 服务状态应为 `active (running)`
- 健康检查应返回 `{"code": 0, "message": "success", "data": {"status": "ok"}}`

---

## 版本间重大变更说明

### 多 LLM 配置支持（feat: 支持多 provider 配置）

**变更内容：**
- 数据库新增 `is_active` 字段到 `llm_configs` 表
- 支持为每个用户配置多个 LLM provider（如 OpenAI、Claude、本地模型等）
- 每个用户可选择一个"激活"的配置用于聊天
- 新增 `provider` 字段的唯一约束 `(user_id, provider)`

**数据库迁移：**
- 迁移文件：`5b0d2d3e48aa_support_multiple_llm_configs.py`
- 使用 `batch_alter_table` 确保 SQLite 兼容性
- 自动将现有配置的 `is_active` 设为 0
- 删除旧的唯一索引 `idx_llm_configs_user_id_unique`
- 创建新的唯一约束 `uq_user_provider`

**影响范围：**
- 前端：LLM 配置页面 UI 变更，支持多配置管理
- 后端：聊天 API 优先使用激活的配置，无激活配置时回退到第一个
- API：`/api/v1/llm-config` 端点行为变更

**更新后操作：**
- 首次使用聊天功能时，系统会自动将第一个配置设为激活状态
- 如需切换激活配置，前往"设置 > LLM 配置"页面操作

### FTS5 全文搜索自动修复

**变更内容：**
- 启动时自动检测 FTS5 索引是否损坏
- 如损坏，自动删除并重建 FTS5 虚拟表和触发器
- 重建后自动填充索引数据

**影响范围：**
- 仅后端，无 API 变更
- 首次启动时可能有短暂延迟（重建索引）

### API Key 掩码逻辑统一

**变更内容：**
- 统一 LLM 和 RAG 配置的 API Key 掩码逻辑
- 更新配置时，如果 API Key 包含 `***`，保留原有加密值
- 测试连接功能支持使用掩码 Key

**影响范围：**
- 前端：API Key 显示和编辑行为变更
- 后端：配置更新和测试连接 API 行为变更

---

## 更新后验证

### 1. 检查服务状态

```bash
sudo systemctl status boke
sudo systemctl status nginx
sudo systemctl status redis
```

所有服务应为 `active (running)` 状态。

### 2. 测试 API 接口

```bash
# 健康检查
curl -s http://localhost:8000/api/v1/health

# 登录测试
curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "你的管理员密码"}'
```

### 3. 浏览器访问

访问 `http://你的服务器IP`，验证：
- 页面正常加载
- 可以登录
- 聊天功能正常
- 文档上传正常
- 设置页面正常

### 4. 检查日志

```bash
# 查看最近日志
sudo journalctl -u boke -n 100 --no-pager

# 实时查看日志
sudo journalctl -u boke -f
```

确认无错误日志。

---

## 回滚操作

如果更新后出现问题，可以回滚到更新前的版本。

### 1. 停止服务

```bash
sudo systemctl stop boke
sudo systemctl stop boke-celery 2>/dev/null || true
```

### 2. 恢复数据库

```bash
cd ~/BoKe

# 查看可用的备份
ls -la data/app.db.backup.*

# 恢复最新的备份（替换 YYYYMMDD_HHMMSS 为实际时间戳）
cp data/app.db.backup.YYYYMMDD_HHMMSS data/app.db
```

### 3. 回滚代码

```bash
cd ~/BoKe

# 查看更新前的版本号（从 git log 中找到）
git log --oneline -20

# 回滚到指定版本
git checkout <更新前的commit-hash>

# 或者回滚到上一个版本
git checkout HEAD~1
```

### 4. 恢复配置文件（如果需要）

```bash
cd ~/BoKe
cp .env.backup.YYYYMMDD_HHMMSS .env
```

### 5. 重新安装依赖并重启

```bash
cd ~/BoKe
source venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
npm run build
cd ..

sudo systemctl daemon-reload
sudo systemctl start boke
sudo systemctl start boke-celery 2>/dev/null || true
```

### 6. 验证回滚成功

```bash
sudo systemctl status boke
curl -s http://localhost:8000/api/v1/health
git log --oneline -1
```

---

## 常见问题排查

### 问题 1：数据库迁移失败

**症状：** `alembic upgrade head` 报错

**可能原因及解决：**

1. **数据库文件不存在**
   ```bash
   mkdir -p data
   chmod 755 data
   alembic upgrade head
   ```

2. **迁移版本冲突**
   ```bash
   # 查看当前数据库版本
   alembic current
   
   # 查看历史版本
   alembic history
   
   # 如果版本不一致，强制标记为当前版本
   alembic stamp head
   alembic upgrade head
   ```

3. **SQLite 表已存在**
   ```bash
   # 备份后删除数据库重建
   cp data/app.db data/app.db.broken
   rm data/app.db
   alembic upgrade head
   ```

4. **模块导入路径问题**
   ```bash
   # 确保在项目根目录运行
   cd ~/BoKe
   alembic upgrade head
   ```

### 问题 2：前端构建失败

**症状：** `npm run build` 报错

**可能原因及解决：**

1. **Node.js 版本过低**
   ```bash
   node --version  # 需要 >= 18
   # 升级 Node.js
   curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
   sudo apt install -y nodejs
   ```

2. **依赖未安装或损坏**
   ```bash
   cd ~/BoKe/frontend
   rm -rf node_modules package-lock.json
   npm install
   npm run build
   ```

3. **内存不足**
   ```bash
   # 创建 swap 分区
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

### 问题 3：服务启动失败

**症状：** `sudo systemctl start boke` 失败

**排查步骤：**
```bash
# 查看详细错误日志
sudo journalctl -u boke -n 50 --no-pager

# 检查端口是否被占用
sudo lsof -i :8000

# 检查文件权限
ls -la ~/BoKe/.env
ls -la ~/BoKe/data/
```

**常见原因及解决：**

1. **端口被占用**
   ```bash
   # 停止占用端口的进程
   sudo kill <PID>
   # 或修改端口号
   sudo nano /etc/systemd/system/boke.service
   # 修改 ExecStart 中的 --port 参数
   sudo systemctl daemon-reload
   sudo systemctl start boke
   ```

2. **权限问题**
   ```bash
   sudo chown -R boke:boke ~/BoKe
   chmod 600 ~/BoKe/.env
   chmod -R 755 ~/BoKe/data
   chmod -R 755 ~/BoKe/storage
   ```

3. **环境变量缺失**
   ```bash
   # 检查 .env 文件
   cat ~/BoKe/.env | grep -E "^(JWT_SECRET_KEY|ADMIN_PASSWORD)"
   # 确保必填变量已设置
   ```

### 问题 4：Nginx 502 Bad Gateway

**症状：** 访问网站显示 502 错误

**排查步骤：**
```bash
# 检查后端服务状态
sudo systemctl status boke

# 检查 Nginx 错误日志
sudo tail -20 /var/log/nginx/error.log

# 检查 Nginx 配置
sudo nginx -t
```

**常见原因及解决：**

1. **后端服务未启动**
   ```bash
   sudo systemctl start boke
   ```

2. **Nginx 配置端口不匹配**
   ```bash
   sudo nano /etc/nginx/sites-available/boke
   # 检查 proxy_pass 端口是否与 boke.service 中的 --port 一致
   sudo systemctl reload nginx
   ```

3. **SELinux 阻止代理（CentOS）**
   ```bash
   sudo setsebool -P httpd_can_network_connect 1
   ```

### 问题 5：聊天功能异常

**症状：** 发送消息后无响应或报错

**排查步骤：**
```bash
# 查看后端日志
sudo journalctl -u boke -n 50 --no-pager

# 测试 LLM 配置
curl -s -X GET http://localhost:8000/api/v1/llm-config \
  -H "Authorization: Bearer <your-token>"
```

**常见原因及解决：**

1. **LLM 配置未设置或已过期**
   - 前往"设置 > LLM 配置"页面检查
   - 重新配置 API Key

2. **API Key 掩码问题**
   - 更新后首次配置时，如果看到 `***`，需要重新输入完整的 API Key
   - 或者直接点击"保存"保留原有配置

3. **多配置激活问题**
   - 前往"设置 > LLM 配置"页面
   - 确保有一个配置被标记为"当前使用"
   - 如果没有，点击某个配置的"设为当前"按钮

### 问题 6：FTS5 全文搜索异常

**症状：** 文档搜索功能不工作

**排查步骤：**
```bash
# 查看启动日志中是否有 FTS5 相关信息
sudo journalctl -u boke | grep -i fts

# 手动重建 FTS5 索引
cd ~/BoKe
source venv/bin/activate
python3 -c "
from backend.database import SessionLocal
from sqlalchemy import text
db = SessionLocal()
db.execute(text(\"INSERT INTO documents_fts(documents_fts) VALUES('rebuild')\"))
db.commit()
db.close()
print('FTS5 索引已重建')
"
```

### 问题 7：更新后配置丢失

**症状：** 更新后 LLM 或 RAG 配置需要重新设置

**解决：**
- 检查数据库备份是否正确恢复
- 如果配置确实丢失，需要重新在"设置"页面配置
- 配置保存在数据库中，不在代码中，正常更新不会丢失

---

## 更新检查清单

更新前请确认以下事项：

- [ ] 已备份数据库 (`data/app.db`)
- [ ] 已备份配置文件 (`.env`)
- [ ] 已记录当前版本号 (`git log --oneline -1`)
- [ ] 已停止相关服务 (`boke`, `boke-celery`)
- [ ] 磁盘空间充足 (至少 2GB)
- [ ] 网络连接正常 (需要拉取代码和依赖)

更新后请验证：

- [ ] 数据库迁移成功 (`alembic current` 显示最新版本)
- [ ] 前端构建成功 (`frontend/dist/` 目录存在)
- [ ] 服务启动成功 (`systemctl status boke` 显示 active)
- [ ] 健康检查通过 (`curl http://localhost:8000/api/v1/health`)
- [ ] 页面可以正常访问
- [ ] 登录功能正常
- [ ] 聊天功能正常
- [ ] 无错误日志 (`journalctl -u boke -n 50`)

---

## 联系支持

如果按照本文档操作后仍无法解决问题，请提供以下信息：

1. 当前版本号：`git log --oneline -1`
2. 目标版本号：要更新到的版本
3. 错误日志：`sudo journalctl -u boke -n 100 --no-pager`
4. 系统信息：`uname -a` 和 `cat /etc/os-release`
5. Python 版本：`python3 --version`
6. Node.js 版本：`node --version`

---

*最后更新：2026-05-13*
