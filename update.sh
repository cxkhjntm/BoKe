#!/usr/bin/env bash
set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*"; }
step()  { echo -e "${CYAN}[步骤]${NC} $*"; }

fail_and_exit() {
    local step_num="$1"
    local step_desc="$2"
    echo ""
    error "========================================="
    error "更新失败！"
    error "========================================="
    error ""
    error "失败阶段: 阶段 ${step_num} (对应手动步骤 ${step_num})"
    error "失败操作: ${step_desc}"
    error ""
    error "请从 UPDATE.md 的「手动更新」→「步骤 ${step_num}」开始继续操作。"
    error "文档位置: ~/BoKe/UPDATE.md"
    error ""
    exit 1
}

PROJECT_DIR="$SCRIPT_DIR"
VENV_DIR="$PROJECT_DIR/venv"

echo ""
info "========================================="
info "  BoKe 一键更新脚本"
info "========================================="
echo ""

# ==================== 阶段 1：停止服务 ====================
step "阶段 1/8 — 停止服务 (对应手动步骤 1)"

sudo systemctl stop boke 2>/dev/null || true
sudo systemctl stop boke-celery 2>/dev/null || true
info "服务已停止"
echo ""

# ==================== 阶段 2：备份数据库 ====================
step "阶段 2/8 — 备份数据库 (对应手动步骤 2)"

BACKUP_FILE="data/app.db.backup.$(date +%Y%m%d_%H%M%S)"
if [ -f data/app.db ]; then
    cp data/app.db "$BACKUP_FILE"
    info "数据库已备份到: $BACKUP_FILE"
else
    warn "数据库文件不存在，跳过备份"
fi
echo ""

# ==================== 阶段 3：拉取最新代码 ====================
step "阶段 3/8 — 拉取最新代码 (对应手动步骤 3)"

# 记录更新前版本
BEFORE_VERSION=$(git log --oneline -1)
info "更新前版本: $BEFORE_VERSION"

# 暂存本地修改
STASHED=false
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
    info "检测到本地修改，暂存中..."
    git stash push -m "auto-stash before update $(date +%Y%m%d_%H%M%S)"
    STASHED=true
    info "本地修改已暂存"
else
    info "没有本地修改，跳过暂存"
fi

# 拉取更新
info "拉取远程更新..."
if ! git fetch origin; then
    fail_and_exit 3 "git fetch origin 失败（网络问题或远程仓库不存在）"
fi

if ! git pull origin main; then
    fail_and_exit 3 "git pull origin main 失败（可能存在冲突）"
fi

# 恢复本地修改
if [ "$STASHED" = true ]; then
    info "恢复本地修改..."
    if ! git stash pop; then
        warn "========================================="
        warn "恢复本地修改时出现冲突！"
        warn "========================================="
        warn ""
        warn "请手动解决冲突后继续："
        warn "  1. 查看冲突文件: git status"
        warn "  2. 编辑冲突文件，解决冲突标记"
        warn "  3. 标记已解决: git add <冲突文件>"
        warn "  4. 继续后续步骤（从阶段 4 开始）"
        warn ""
        warn "如果不想保留本地修改: git checkout -- ."
        warn ""
        fail_and_exit 3 "git stash pop 冲突（需手动解决）"
    fi
    info "本地修改已恢复"
else
    info "没有需要恢复的本地修改"
fi

AFTER_VERSION=$(git log --oneline -1)
info "更新后版本: $AFTER_VERSION"
echo ""

# ==================== 阶段 4：更新 Python 依赖 ====================
step "阶段 4/8 — 更新 Python 依赖 (对应手动步骤 4)"

if [ ! -d "$VENV_DIR" ]; then
    error "虚拟环境不存在: $VENV_DIR"
    fail_and_exit 4 "虚拟环境目录不存在"
fi

source "$VENV_DIR/bin/activate"

if ! pip install -q -r requirements.txt; then
    fail_and_exit 4 "pip install 失败（依赖安装错误）"
fi
info "Python 依赖已更新"
echo ""

# ==================== 阶段 5：运行数据库迁移 ====================
step "阶段 5/8 — 运行数据库迁移 (对应手动步骤 5)"

set -a
source .env
set +a

if ! alembic upgrade head; then
    fail_and_exit 5 "alembic upgrade head 失败（数据库迁移错误）"
fi
info "数据库迁移完成"
echo ""

# ==================== 阶段 6：构建前端 ====================
step "阶段 6/8 — 构建前端 (对应手动步骤 6)"

cd frontend

if ! npm install --silent 2>/dev/null; then
    cd "$PROJECT_DIR"
    fail_and_exit 6 "npm install 失败（前端依赖安装错误）"
fi

if ! npm run build; then
    cd "$PROJECT_DIR"
    fail_and_exit 6 "npm run build 失败（前端构建错误）"
fi

cd "$PROJECT_DIR"
info "前端构建完成"
echo ""

# ==================== 阶段 7：重启服务 ====================
step "阶段 7/8 — 重启服务 (对应手动步骤 7+8)"

sudo systemctl daemon-reload

if ! sudo systemctl start boke; then
    fail_and_exit 8 "sudo systemctl start boke 失败"
fi

sudo systemctl start boke-celery 2>/dev/null || true
info "服务已重启"
echo ""

# ==================== 阶段 8：验证服务状态 ====================
step "阶段 8/8 — 验证服务状态 (对应手动步骤 9)"

sleep 2

if sudo systemctl is-active --quiet boke; then
    info "boke 服务运行正常"
else
    error "boke 服务未正常启动"
    error "请查看日志: sudo journalctl -u boke -n 50"
    fail_and_exit 9 "服务启动验证失败"
fi

# 健康检查
sleep 1
HEALTH_RESPONSE=$(curl -s http://localhost:8000/api/v1/health 2>/dev/null || echo "")
if echo "$HEALTH_RESPONSE" | grep -q '"status":"ok"'; then
    info "健康检查通过"
else
    warn "健康检查未通过，可能需要等待几秒后重试"
    warn "手动验证: curl http://localhost:8000/api/v1/health"
fi

echo ""
info "========================================="
info "  更新完成！"
info "========================================="
echo ""
info "更新前版本: $BEFORE_VERSION"
info "更新后版本: $AFTER_VERSION"
echo ""
info "如有问题，请查看日志: sudo journalctl -u boke -f"
echo ""
