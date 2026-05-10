# BoKe 个人研究资料管理系统 -- 完整部署操作手册

本手册指导你在一台全新的纯净 Linux 服务器上完成 BoKe 系统的部署。从操作系统初始化到应用正式运行，每一步都配有可直接复制执行的命令和验证方法。

---

## 目录

- [第一章：服务器基础环境准备](#第一章服务器基础环境准备)
- [第二章：安装 Python 3.11+](#第二章安装-python-311)
- [第三章：安装 Node.js 18+](#第三章安装-nodejs-18)
- [第四章：安装和配置 Redis](#第四章安装和配置-redis)
- [第五章：安装 Nginx](#第五章安装-nginx)
- [第六章：克隆项目和配置](#第六章克隆项目和配置)
- [第七章：创建 Python 虚拟环境和安装依赖](#第七章创建-python-虚拟环境和安装依赖)
- [第八章：构建前端](#第八章构建前端)
- [第九章：运行数据库迁移](#第九章运行数据库迁移)
- [第十章：配置 Nginx 反向代理](#第十章配置-nginx-反向代理)
- [第十一章：使用 Systemd 管理应用](#第十一章使用-systemd-管理应用)
- [第十二章：配置 Celery Worker（可选）](#第十二章配置-celery-worker可选)
- [第十三章：防火墙配置](#第十三章防火墙配置)
- [第十四章：验证部署](#第十四章验证部署)
- [第十五章：常见问题排查](#第十五章常见问题排查)
- [第十六章：维护和更新](#第十六章维护和更新)
- [附录：环境变量完整参考表](#附录环境变量完整参考表)

---

## 第一章：服务器基础环境准备

### 1.1 系统要求

| 项目 | 最低配置 | 推荐配置 |
|------|---------|---------|
| CPU | 1 核 | 2 核 |
| 内存 | 1 GB | 4 GB |
| 磁盘 | 20 GB | 50 GB（取决于文档存储量） |
| 操作系统 | Ubuntu 22.04 / Debian 12 / CentOS 8+ | Ubuntu 22.04 LTS |
| 架构 | x86_64 / arm64 | x86_64 |

本手册以 **Ubuntu 22.04 LTS** 为例进行说明。CentOS / Debian 的差异会在对应步骤中标注。

### 1.2 系统更新

首次登录服务器后，先更新系统软件包到最新版本。

**Ubuntu / Debian：**

```bash
sudo apt update && sudo apt upgrade -y
```

**CentOS / RHEL：**

```bash
sudo dnf update -y
```

验证系统更新完成：

```bash
cat /etc/os-release
```

你应该能看到类似 `VERSION_ID="22.04"` 的输出。

### 1.3 安装基础工具

这些工具在后续步骤中都会用到。

**Ubuntu / Debian：**

```bash
sudo apt install -y curl wget git build-essential software-properties-common apt-transport-https ca-certificates gnupg lsb-release
```

**CentOS / RHEL：**

```bash
sudo dnf install -y curl wget git gcc gcc-c++ make
```

验证基础工具安装：

```bash
curl --version
wget --version | head -1
git --version
gcc --version | head -1
```

每个命令都应该输出对应的版本号，没有报错。

### 1.4 创建部署用户（可选但推荐）

出于安全考虑，建议不要直接使用 root 用户运行应用。

```bash
sudo adduser boke
sudo usermod -aG sudo boke
```

切换到新用户：

```bash
su - boke
```

后续所有操作建议在此用户下执行。需要 sudo 权限时在命令前加 `sudo`。

---

## 第二章：安装 Python 3.11+

BoKe 后端基于 Python 3.11 开发。系统自带的 Python 版本可能较低，需要手动安装。

### 2.1 Ubuntu / Debian 安装方法

```bash
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install -y python3.11 python3.11-venv python3.11-dev python3.11-distutils
```

如果系统已有 python3 但版本不够，需要设置 python3.11 为默认：

```bash
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
```

### 2.2 CentOS / RHEL 安装方法

CentOS 8+ 和 RHEL 8+ 通常自带 Python 3.9，需要从源码编译安装 3.11：

```bash
sudo dnf install -y openssl-devel bzip2-devel libffi-devel zlib-devel readline-devel sqlite-devel
cd /tmp
wget https://www.python.org/ftp/python/3.11.9/Python-3.11.9.tgz
tar xzf Python-3.11.9.tgz
cd Python-3.11.9
./configure --enable-optimizations
make -j$(nproc)
sudo make altinstall
```

创建软链接：

```bash
sudo ln -sf /usr/local/bin/python3.11 /usr/bin/python3
sudo ln -sf /usr/local/bin/pip3.11 /usr/bin/pip3
```

### 2.3 验证安装

```bash
python3 --version
```

预期输出（版本号必须 >= 3.11）：

```
Python 3.11.x
```

### 2.4 安装 pip 和 venv

**Ubuntu / Debian：**

```bash
sudo apt install -y python3-pip
```

pip 和 venv 通常随 python3.11-venv 包一起安装。验证：

```bash
pip3 --version
python3 -m venv --help > /dev/null && echo "venv OK"
```

**CentOS / RHEL（源码编译后已自带 pip）：**

```bash
pip3 --version
```

如果 pip3 不存在：

```bash
curl -sS https://bootstrap.pypa.io/get-pip.py | python3
```

---

## 第三章：安装 Node.js 18+

前端构建需要 Node.js 18 或更高版本。

### 3.1 方法一：使用 NodeSource 安装（推荐）

**Ubuntu / Debian：**

```bash
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs
```

**CentOS / RHEL：**

```bash
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo dnf install -y nodejs
```

### 3.2 方法二：使用 nvm 安装

如果你需要在同一台服务器上管理多个 Node.js 版本，可以使用 nvm：

```bash
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
source ~/.bashrc
nvm install 18
nvm use 18
nvm alias default 18
```

### 3.3 验证安装

```bash
node --version
npm --version
```

预期输出：

```
v18.x.x
9.x.x
```

node 版本号必须 >= 18.0.0。

---

## 第四章：安装和配置 Redis

Redis 用于 Celery 任务队列的消息中间件。如果你不需要异步文档处理功能，可以跳过本章。但强烈建议安装，以获得更好的文档处理体验。

### 4.1 安装 Redis

**Ubuntu / Debian：**

```bash
sudo apt install -y redis-server
```

**CentOS / RHEL：**

```bash
sudo dnf install -y redis
```

### 4.2 启动 Redis

```bash
sudo systemctl start redis
```

### 4.3 设置开机自启

```bash
sudo systemctl enable redis-server
```

> **注意：** 在某些系统上（如 Ubuntu），Redis 的服务名为 `redis-server` 而非 `redis`。如果执行 `sudo systemctl enable redis` 提示找不到服务，请改用 `sudo systemctl enable redis-server`。

预期输出：

```
Created symlink /etc/systemd/system/multi-user.target.wants/redis-server.service → /lib/systemd/system/redis-server.service.
```

### 4.4 验证 Redis

```bash
redis-cli ping
```

预期输出：

```
PONG
```

如果返回 `PONG`，说明 Redis 已正常运行。

### 4.5 配置 Redis 密码（推荐）

编辑 Redis 配置文件：

```bash
sudo nano /etc/redis/redis.conf
```

找到 `# requirepass foobared` 这一行，去掉注释并设置一个强密码：

```
requirepass your_strong_redis_password_here
```

同时确认以下关键参数：

```
bind 127.0.0.1
port 6379
daemonize no
maxmemory 256mb
maxmemory-policy allkeys-lru
```

保存文件后重启 Redis：

```bash
sudo systemctl restart redis
```

验证密码是否生效：

```bash
redis-cli -a your_strong_redis_password_here ping
```

预期输出 `PONG`。

如果设置了 Redis 密码，后续在 `.env` 文件中的 `REDIS_URL` 需要包含密码：

```
REDIS_URL=redis://:your_strong_redis_password_here@localhost:6379/0
```

### 4.6 验证 Redis 版本

```bash
redis-server --version
```

建议 Redis 版本 >= 6.0。

---

## 第五章：安装 Nginx

Nginx 用作反向代理，将外部请求转发到后端 FastAPI 应用，同时直接提供前端静态文件。

### 5.1 安装 Nginx

**Ubuntu / Debian：**

```bash
sudo apt install -y nginx
```

**CentOS / RHEL：**

```bash
sudo dnf install -y nginx
```

### 5.2 启动 Nginx

```bash
sudo systemctl start nginx
```

### 5.3 设置开机自启

```bash
sudo systemctl enable nginx
```

### 5.4 验证安装

```bash
curl -s http://localhost | head -20
```

你应该能看到 Nginx 的默认欢迎页面 HTML。如果没有看到，检查 Nginx 是否正在运行：

```bash
sudo systemctl status nginx
```

确认状态为 `active (running)`。

---

## 第六章：克隆项目和配置

### 6.1 克隆项目

```bash
cd ~
git clone https://github.com/cxkhjntm/claude_code.git BoKe
cd BoKe
```

验证克隆成功：

```bash
ls -la
```

你应该能看到 `backend/`、`frontend/`、`requirements.txt`、`.env.example` 等文件和目录。

### 6.2 复制环境配置文件

```bash
cp .env.example .env
```

> **注意：** 如果提示 `.env.example` 文件不存在，可能是因为以 `.` 开头的文件默认被隐藏。使用 `ls -la` 查看所有文件（包括隐藏文件）。如果文件确实丢失，可以通过 Git 恢复：
>
> ```bash
> git checkout -- .env.example
> ```

### 6.3 生成 JWT 密钥

```bash
openssl rand -hex 32
```

命令会输出一串 64 位的十六进制字符串，类似：

```
a1b2c3d4e5f6...（共64个字符）
```

复制这串字符，下一步要用。

### 6.4 编辑 .env 文件

```bash
nano .env
```

根据以下说明修改每个配置项：

```ini
# 必填项 - JWT 签名密钥（上一步生成的字符串）
JWT_SECRET_KEY=粘贴你生成的64位密钥

# 必填项 - 管理员密码（设置一个强密码）
ADMIN_PASSWORD=你的管理员密码

# 管理员用户名（可选，默认 admin）
ADMIN_USERNAME=admin

# 数据库路径（使用默认值即可）
DATABASE_URL=sqlite:///./data/app.db

# 文件存储路径（使用默认值即可）
STORAGE_PATH=./storage

# 最大上传文件大小，单位 MB
MAX_UPLOAD_SIZE_MB=50

# 允许上传的文件扩展名
ALLOWED_EXTENSIONS=pdf,docx,md,png,jpg,jpeg

# 头像上传大小限制，单位 MB
IMAGE_MAX_UPLOAD_SIZE_MB=5

# 允许的头像文件扩展名
IMAGE_ALLOWED_EXTENSIONS=png,jpg,jpeg,webp,gif

# CORS 允许的来源（部署到生产环境时改为你的域名或服务器 IP）
CORS_ORIGINS=http://你的服务器IP或域名

# Redis 地址（如果设置了 Redis 密码，格式为 redis://:密码@localhost:6379/0）
REDIS_URL=redis://localhost:6379/0

# 登录频率限制（每分钟每个 IP 最多尝试次数）
RATE_LIMIT_LOGIN=5

# 聊天超时时间（秒）
CHAT_MAX_TIMEOUT=120

# 聊天消息最大长度（字符）
CHAT_MAX_MESSAGE_LENGTH=8000

# 聊天频率限制（每分钟）
CHAT_RATE_LIMIT_PER_MINUTE=20

# 是否开放注册（生产环境建议关闭）
REGISTRATION_ENABLED=false

# 日志级别
LOG_LEVEL=INFO
```

保存文件：按 `Ctrl+X`，然后按 `Y`，最后按 `Enter`。

### 6.5 设置 .env 文件权限

```bash
chmod 600 .env
```

验证权限：

```bash
ls -la .env
```

预期输出应类似：

```
-rw------- 1 boke boke xxx xxx xx xx:xx .env
```

权限必须是 `-rw-------`（即 600），确保只有文件所有者可以读写。

### 6.6 创建必要目录

```bash
mkdir -p data storage
```

验证目录创建：

```bash
ls -ld data storage
```

应输出两个目录的详细信息。

---

## 第七章：创建 Python 虚拟环境和安装依赖

### 7.1 创建虚拟环境

```bash
python3 -m venv venv
```

### 7.2 激活虚拟环境

```bash
source venv/bin/activate
```

激活后命令行提示符会变成类似 `(venv) boke@server:~/BoKe$` 的形式。

验证虚拟环境激活：

```bash
which python
```

预期输出应包含 `/venv/bin/python` 路径。

### 7.3 升级 pip

```bash
pip install --upgrade pip
```

### 7.4 安装 Python 依赖

```bash
pip install -r requirements.txt
```

这个过程可能需要几分钟，取决于网络速度。如果遇到网络问题，可以使用国内镜像源：

```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 7.5 验证依赖安装

```bash
python -c "import fastapi; print('FastAPI', fastapi.__version__)"
python -c "import uvicorn; print('Uvicorn OK')"
python -c "import sqlalchemy; print('SQLAlchemy', sqlalchemy.__version__)"
python -c "import alembic; print('Alembic OK')"
```

每条命令都应该输出对应的版本号或 OK，没有 `ModuleNotFoundError` 报错。

---

## 第八章：构建前端

### 8.1 进入前端目录

```bash
cd ~/BoKe/frontend
```

### 8.2 安装前端依赖

```bash
npm install
```

如果 npm 速度较慢，可以设置淘宝镜像：

```bash
npm config set registry https://registry.npmmirror.com
npm install
```

### 8.3 构建前端产物

```bash
npm run build
```

构建成功后会输出类似以下信息：

```
vite v5.x.x building for production...
✓ xx modules transformed.
dist/index.html           x.xx kB
dist/assets/index-xxx.js  xxx.xx kB
dist/assets/index-xxx.css xx.xx kB
✓ built in x.xx s
```

### 8.4 验证构建产物

```bash
ls -la dist/
ls -la dist/assets/
```

`dist/` 目录下应该有 `index.html` 文件，`assets/` 目录下应该有 `.js` 和 `.css` 文件。

### 8.5 返回项目根目录

```bash
cd ~/BoKe
```

---

## 第九章：运行数据库迁移

### 9.1 确保在项目根目录

```bash
cd ~/BoKe
```

### 9.2 确保虚拟环境已激活

```bash
source venv/bin/activate
```

### 9.3 加载环境变量并运行迁移

```bash
set -a && source .env && set +a
alembic upgrade head
```

预期输出类似：

```
INFO  [alembic] Running upgrade -> xxxx, Initial migration
```

如果没有输出错误信息，说明迁移成功。

### 9.4 验证数据库文件

```bash
ls -la data/app.db
```

应该能看到 `data/app.db` 文件，大小不为 0。

---

## 第十章：配置 Nginx 反向代理

### 10.1 复制 Nginx 配置文件

```bash
sudo cp ~/BoKe/nginx.conf /etc/nginx/sites-available/boke
```

### 10.2 修改配置文件

```bash
sudo nano /etc/nginx/sites-available/boke
```

> **nano 编辑器操作提示：**
> - **保存文件：** 按 `Ctrl + O`（字母 O，不是数字 0），然后按 `Enter` 确认文件名（保持原文件名不变）。
> - **退出编辑器：** 按 `Ctrl + X`。

需要修改两个地方：

**1. 修改 `server_name`**

找到 `server_name _;` 这一行，将 `_` 替换为你的实际域名或服务器 IP：

```
server_name your-domain.com;
```

如果没有域名，使用服务器 IP：

```
server_name 192.168.1.100;
```

**2. 修改前端静态文件路径**

找到 `root /home/ubuntuuser/BoKe/frontend/dist;` 这一行，替换为你的实际路径：

```
root /home/boke/BoKe/frontend/dist;
```

如果你使用的不是 `boke` 用户，请替换为实际的用户名。

保存文件：`Ctrl+X`，`Y`，`Enter`。

### 10.3 创建软链接

```bash
sudo ln -sf /etc/nginx/sites-available/boke /etc/nginx/sites-enabled/
```

### 10.4 删除默认配置（可选）

```bash
sudo rm -f /etc/nginx/sites-enabled/default
```

### 10.5 测试 Nginx 配置

```bash
sudo nginx -t
```

预期输出：

```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

如果出现错误，检查配置文件中的路径是否正确。

### 10.6 重载 Nginx

```bash
sudo systemctl reload nginx
```

---

## 第十一章：使用 Systemd 管理应用

使用 Systemd 可以让 BoKe 后端作为系统服务运行，支持开机自启和自动重启。

### 11.1 创建 boke.service 文件

```bash
sudo nano /etc/systemd/system/boke.service
```

将以下内容完整写入文件（根据你的实际情况修改路径和用户名）：

```ini
[Unit]
Description=BoKe Personal Research Manager
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=boke
Group=boke
WorkingDirectory=/home/boke/BoKe
Environment="PATH=/home/boke/BoKe/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/boke/BoKe/.env
ExecStart=/home/boke/BoKe/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
TimeoutStartSec=30
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

**注意：** 将 `/home/boke/BoKe` 替换为你的实际项目路径。如果用户名不是 `boke`，也要相应修改 `User` 和 `Group`。

保存文件：`Ctrl+X`，`Y`，`Enter`。

### 11.2 重载 Systemd 配置

```bash
sudo systemctl daemon-reload
```

### 11.3 设置开机自启

```bash
sudo systemctl enable boke
```

### 11.4 启动服务

```bash
sudo systemctl start boke
```

### 11.5 查看服务状态

```bash
sudo systemctl status boke
```

预期输出应包含 `active (running)` 字样：

```
● boke.service - BoKe Personal Research Manager
     Loaded: loaded (/etc/systemd/system/boke.service; enabled; vendor preset: enabled)
     Active: active (running) since ...
     ...
```

如果状态不是 `active (running)`，查看日志排查问题：

```bash
sudo journalctl -u boke -n 50 --no-pager
```

### 11.6 查看实时日志

```bash
sudo journalctl -u boke -f
```

按 `Ctrl+C` 退出实时日志查看。

---

## 第十二章：配置 Celery Worker（可选）

Celery Worker 用于异步处理文档（如 PDF 解析、文本提取等）。如果你不配置 Celery，系统会使用同步模式处理文档，功能不受影响，只是大量文档上传时处理速度较慢。

### 12.1 前提条件

确保 Redis 已安装并运行（参见第四章）。

### 12.2 创建 boke-celery.service 文件

```bash
sudo nano /etc/systemd/system/boke-celery.service
```

将以下内容完整写入文件：

```ini
[Unit]
Description=BoKe Celery Worker
After=network.target redis.service boke.service
Wants=redis.service

[Service]
Type=simple
User=boke
Group=boke
WorkingDirectory=/home/boke/BoKe
Environment="PATH=/home/boke/BoKe/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/boke/BoKe/.env
ExecStart=/home/boke/BoKe/venv/bin/celery -A backend.celery_app worker --loglevel=info --concurrency=2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**注意：** 同样需要将路径替换为你的实际项目路径。`--concurrency=2` 表示同时处理 2 个任务，可根据服务器 CPU 核心数调整。

### 12.3 重载 Systemd 配置

```bash
sudo systemctl daemon-reload
```

### 12.4 设置开机自启

```bash
sudo systemctl enable boke-celery
```

### 12.5 启动 Celery Worker

```bash
sudo systemctl start boke-celery
```

### 12.6 验证 Celery 状态

```bash
sudo systemctl status boke-celery
```

确认状态为 `active (running)`。

---

## 第十三章：防火墙配置

> **提示：** 如果你使用的是阿里云、腾讯云、华为云等云服务器厂商，通常默认已经配置好了安全组规则（放行 22、80、443 端口），可以跳过本章。如有需要，请到云服务器控制台的安全组中确认规则。

### 13.1 UFW（Ubuntu / Debian）

Ubuntu 默认使用 UFW 防火墙。

```bash
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

启用时会提示 "Command may disrupt existing SSH connections"，输入 `y` 确认。

验证防火墙规则：

```bash
sudo ufw status
```

预期输出：

```
Status: active

To                         Action      From
--                         ------      ----
22/tcp                     ALLOW       Anywhere
80/tcp                     ALLOW       Anywhere
443/tcp                    ALLOW       Anywhere
```

### 13.2 firewalld（CentOS / RHEL）

```bash
sudo firewall-cmd --permanent --add-service=ssh
sudo firewall-cmd --permanent --add-service=http
sudo firewall-cmd --permanent --add-service=https
sudo firewall-cmd --reload
```

验证防火墙规则：

```bash
sudo firewall-cmd --list-all
```

### 13.3 关闭 8000 端口对外访问

BoKe 后端监听在 127.0.0.1:8000，只接受来自 Nginx 的本地请求。在 `boke.service` 文件中已经设置了 `--host 127.0.0.1`，所以 8000 端口不会暴露到外网。

如果你之前修改为 `--host 0.0.0.0`，需要通过防火墙阻止外部访问 8000 端口：

**UFW：**

```bash
sudo ufw deny 8000/tcp
```

**firewalld：**

```bash
sudo firewall-cmd --permanent --remove-port=8000/tcp
sudo firewall-cmd --reload
```

---

## 第十四章：验证部署

完成以上所有步骤后，按以下顺序验证部署是否成功。

### 14.1 检查服务状态

```bash
sudo systemctl status boke
sudo systemctl status nginx
sudo systemctl status redis
```

三个服务都应该是 `active (running)` 状态。

如果配置了 Celery：

```bash
sudo systemctl status boke-celery
```

### 14.2 访问 Web UI

在浏览器中访问：

```
http://你的服务器IP
```

你应该能看到 BoKe 的登录页面。

### 14.3 访问 API 文档

在浏览器中访问：

```
http://你的服务器IP/api/v1/health
```

预期返回：

```json
{"code": 0, "message": "success", "data": {"status": "ok"}}
```

### 14.4 测试健康检查接口

```bash
curl -s http://localhost/api/v1/health
```

预期输出：

```json
{"code": 0, "message": "success", "data": {"status": "ok"}}
```

### 14.5 测试登录功能

```bash
curl -s -X POST http://localhost/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "你在.env中设置的管理员密码"}'
```

预期返回包含 `access_token` 和 `refresh_token` 的 JSON：

```json
{"code": 0, "message": "success", "data": {"access_token": "eyJ...", "refresh_token": "eyJ...", "token_type": "bearer"}}
```

如果返回了 token，说明部署成功。你现在可以在浏览器中使用管理员账号登录系统了。

---

## 第十五章：常见问题排查

### 15.1 端口被占用

**症状：** 启动服务时报错 `Address already in use`。

**排查：**

```bash
sudo lsof -i :8000
sudo lsof -i :80
```

**解决：** 找到占用端口的进程并停止它，或者修改 BoKe 的端口号。

修改 `boke.service` 中的 `ExecStart` 行，将 `--port 8000` 改为其他端口（如 8001）。同时修改 `nginx.conf` 中的 `proxy_pass http://127.0.0.1:8000` 为对应端口。

### 15.2 权限问题

**症状：** 服务启动失败，日志中出现 `Permission denied`。

**排查：**

```bash
sudo journalctl -u boke -n 50 --no-pager
```

**解决：** 确保项目目录和文件的所有者正确：

```bash
sudo chown -R boke:boke /home/boke/BoKe
```

确保 `.env` 文件权限正确：

```bash
chmod 600 /home/boke/BoKe/.env
```

确保 `data/` 和 `storage/` 目录可写：

```bash
chmod -R 755 /home/boke/BoKe/data
chmod -R 755 /home/boke/BoKe/storage
```

### 15.3 Python 依赖安装失败

**症状：** `pip install -r requirements.txt` 报错。

**常见原因和解决方法：**

1. **网络超时：** 使用国内镜像源
   ```bash
   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
   ```

2. **缺少系统依赖：** `python-magic` 需要 `libmagic`
   ```bash
   sudo apt install -y libmagic-dev
   ```
   CentOS 下：
   ```bash
   sudo dnf install -y file-devel
   ```

3. **编译错误：** 确保安装了 `build-essential`（Ubuntu）或 `gcc gcc-c++ make`（CentOS）

4. **PyMuPDF 安装失败：** 升级 pip 后重试
   ```bash
   pip install --upgrade pip
   pip install PyMuPDF
   ```

### 15.4 前端构建失败

**症状：** `npm run build` 报错。

**常见原因和解决方法：**

1. **Node.js 版本过低：** 确认版本 >= 18
   ```bash
   node --version
   ```

2. **依赖未安装：** 先运行 `npm install`
   ```bash
   cd ~/BoKe/frontend
   rm -rf node_modules
   npm install
   npm run build
   ```

3. **内存不足：** 小内存服务器构建时可能 OOM
   ```bash
   # 创建 swap 分区
   sudo fallocate -l 2G /swapfile
   sudo chmod 600 /swapfile
   sudo mkswap /swapfile
   sudo swapon /swapfile
   echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
   ```

### 15.5 Redis 连接失败

**症状：** 日志中出现 `Connection refused` 或 `Redis is not running`。

**排查：**

```bash
sudo systemctl status redis
redis-cli ping
```

**解决：**

1. Redis 未启动：
   ```bash
   sudo systemctl start redis
   ```

2. Redis 密码配置错误：检查 `.env` 中 `REDIS_URL` 格式是否正确
   ```
   REDIS_URL=redis://:密码@localhost:6379/0
   ```

3. Redis 绑定了错误的地址：检查 `/etc/redis/redis.conf` 中的 `bind` 配置，确保包含 `127.0.0.1`

### 15.6 数据库迁移失败

**症状：** `alembic upgrade head` 报错。

**排查：**

```bash
cd ~/BoKe
source venv/bin/activate
set -a && source .env && set +a
alembic upgrade head 2>&1
```

**解决：**

1. **数据库文件不存在：** 确保 `data/` 目录存在且可写
   ```bash
   mkdir -p data
   chmod 755 data
   ```

2. **迁移版本冲突：** 如果是从旧版本升级，可能需要 stamp 当前版本
   ```bash
   alembic stamp head
   alembic upgrade head
   ```

3. **alembic.ini 路径问题：** 确保在项目根目录运行命令

4. **模块导入路径问题：** 如果报错 `ModuleNotFoundError` 或类似路径错误，可能是 alembic 无法找到项目模块。执行以下命令修复 `alembic/env.py` 文件：
   ```bash
   sed -i '1i import sys\nimport os\nsys.path.append(os.path.dirname(os.path.dirname(__file__)))\n' alembic/env.py
   ```
   修复后重新运行：
   ```bash
   alembic upgrade head
   ```

### 15.7 Nginx 502 Bad Gateway

**症状：** 访问网站显示 502 错误。

**排查：**

```bash
sudo systemctl status boke
sudo tail -20 /var/log/nginx/error.log
```

**常见原因和解决方法：**

1. **后端服务未启动：**
   ```bash
   sudo systemctl start boke
   ```

2. **后端服务启动失败：** 查看日志
   ```bash
   sudo journalctl -u boke -n 50 --no-pager
   ```

3. **Nginx 配置中的端口不匹配：** 确认 `nginx.conf` 中 `proxy_pass` 的端口和 `boke.service` 中 `--port` 的端口一致

4. **SELinux 阻止了 Nginx 代理（CentOS）：**
   ```bash
   sudo setsebool -P httpd_can_network_connect 1
   ```

### 15.8 CORS 错误

**症状：** 浏览器控制台出现 `Access-Control-Allow-Origin` 相关错误。

**解决：** 编辑 `.env` 文件，将 `CORS_ORIGINS` 设置为你的前端访问地址：

```
CORS_ORIGINS=http://你的域名或IP
```

如果有多个来源，用逗号分隔：

```
CORS_ORIGINS=http://域名A,http://域名B
```

修改后重启服务：

```bash
sudo systemctl restart boke
```

### 15.9 访问服务器报 500 错误

**症状：** Nginx 返回 500 Internal Server Error，Nginx 错误日志中出现 `Permission denied` 相关信息。

**原因：** Nginx 的工作用户（通常是 `www-data`）没有权限访问项目目录或静态文件。

**解决：** 执行以下命令修复权限：

```bash
# 1. 允许 www-data 用户进入 /home/ubuntu 目录（添加执行权限）
sudo chmod 755 /home/ubuntu

# 2. 递归授予 BoKe 目录读取和执行权限给其他用户
sudo chmod -R 755 /home/ubuntu/BoKe

# 3. 确保静态文件目录可读
sudo chmod -R 755 /home/ubuntu/BoKe/frontend/dist

# 4. 重新加载 Nginx
sudo systemctl reload nginx
```

> **注意：** 请将 `/home/ubuntu` 替换为你实际的用户目录路径。如果你使用的用户名不是 `ubuntu`，请相应修改。

---

## 第十六章：维护和更新

### 16.1 更新项目代码

```bash
cd ~/BoKe
git pull origin main
```

拉取代码后，需要重新安装依赖、构建前端、运行迁移：

```bash
source venv/bin/activate
pip install -r requirements.txt

cd frontend
npm install
npm run build
cd ..

set -a && source .env && set +a
alembic upgrade head

sudo systemctl restart boke
```

如果配置了 Celery：

```bash
sudo systemctl restart boke-celery
```

### 16.2 备份数据库

SQLite 数据库是单文件，直接复制即可备份。

```bash
# 停止服务以确保数据一致性
sudo systemctl stop boke

# 备份数据库
cp ~/BoKe/data/app.db ~/BoKe/data/app.db.backup.$(date +%Y%m%d_%H%M%S)

# 重启服务
sudo systemctl start boke
```

如果不想停服务，可以使用 SQLite 的在线备份：

```bash
cd ~/BoKe
source venv/bin/activate
python3 -c "
import sqlite3
src = sqlite3.connect('data/app.db')
dst = sqlite3.connect('data/app.db.backup.$(date +%Y%m%d_%H%M%S)')
src.backup(dst)
src.close()
dst.close()
print('Backup completed')
"
```

定期备份建议使用 crontab：

```bash
crontab -e
```

添加以下内容（每天凌晨 3 点备份）：

```
0 3 * * * cp /home/boke/BoKe/data/app.db /home/boke/BoKe/data/app.db.backup.$(date +\%Y\%m\%d)
```

### 16.3 查看日志

**查看应用日志（实时）：**

```bash
sudo journalctl -u boke -f
```

**查看应用日志（最近 100 行）：**

```bash
sudo journalctl -u boke -n 100 --no-pager
```

**查看 Celery 日志：**

```bash
sudo journalctl -u boke-celery -f
```

**查看 Nginx 访问日志：**

```bash
sudo tail -f /var/log/nginx/access.log
```

**查看 Nginx 错误日志：**

```bash
sudo tail -f /var/log/nginx/error.log
```

### 16.4 重启服务

**重启 BoKe 后端：**

```bash
sudo systemctl restart boke
```

**重启 Nginx：**

```bash
sudo systemctl reload nginx
```

**重启 Redis：**

```bash
sudo systemctl restart redis
```

**重启所有相关服务：**

```bash
sudo systemctl restart redis boke nginx
```

如果配置了 Celery：

```bash
sudo systemctl restart redis boke-celery boke nginx
```

### 16.5 更新依赖

**更新 Python 依赖：**

```bash
cd ~/BoKe
source venv/bin/activate
pip install --upgrade -r requirements.txt
sudo systemctl restart boke
```

**更新前端依赖：**

```bash
cd ~/BoKe/frontend
npm update
npm run build
sudo systemctl reload nginx
```

---

## 附录：环境变量完整参考表

以下是 `.env` 文件中所有支持的环境变量。

| 变量名 | 是否必填 | 默认值 | 说明 |
|--------|---------|--------|------|
| `JWT_SECRET_KEY` | 是 | 无 | JWT 签名密钥，长度必须 >= 32 字符。生成命令：`openssl rand -hex 32` |
| `ADMIN_PASSWORD` | 是 | 无 | 管理员初始密码 |
| `ADMIN_USERNAME` | 否 | `admin` | 管理员用户名 |
| `DATABASE_URL` | 否 | `sqlite:///./data/app.db` | 数据库连接地址 |
| `STORAGE_PATH` | 否 | `./storage` | 文件存储根目录的路径 |
| `MAX_UPLOAD_SIZE_MB` | 否 | `50` | 单个文件最大上传大小，单位 MB |
| `ALLOWED_EXTENSIONS` | 否 | `pdf,docx,md,png,jpg,jpeg` | 允许上传的文件类型，逗号分隔 |
| `IMAGE_MAX_UPLOAD_SIZE_MB` | 否 | `5` | 头像图片最大上传大小，单位 MB |
| `IMAGE_ALLOWED_EXTENSIONS` | 否 | `png,jpg,jpeg,webp,gif` | 允许的头像图片类型，逗号分隔 |
| `CORS_ORIGINS` | 否 | `http://localhost:5173` | CORS 允许的来源地址，逗号分隔 |
| `REDIS_URL` | 否 | `redis://localhost:6379/0` | Redis 连接地址 |
| `RATE_LIMIT_LOGIN` | 否 | `5` | 每分钟每个 IP 的登录尝试次数上限 |
| `CHAT_MAX_TIMEOUT` | 否 | `120` | 聊天请求超时时间，单位秒 |
| `CHAT_MAX_MESSAGE_LENGTH` | 否 | `8000` | 单条聊天消息最大字符数 |
| `CHAT_RATE_LIMIT_PER_MINUTE` | 否 | `20` | 每分钟聊天请求数上限 |
| `REGISTRATION_ENABLED` | 否 | `false` | 是否开放用户注册，`true` 或 `false` |
| `LOG_LEVEL` | 否 | `INFO` | 日志级别，可选 `DEBUG`、`INFO`、`WARNING`、`ERROR` |
| `JWT_ALGORITHM` | 否 | `HS256` | JWT 签名算法 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 否 | `30` | 访问令牌过期时间，单位分钟 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 否 | `7` | 刷新令牌过期时间，单位天 |

---

## 附录：systemd service 文件完整参考

### boke.service

```ini
[Unit]
Description=BoKe Personal Research Manager
After=network.target redis.service
Wants=redis.service

[Service]
Type=simple
User=boke
Group=boke
WorkingDirectory=/home/boke/BoKe
Environment="PATH=/home/boke/BoKe/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/boke/BoKe/.env
ExecStart=/home/boke/BoKe/venv/bin/uvicorn backend.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
TimeoutStartSec=30
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

### boke-celery.service

```ini
[Unit]
Description=BoKe Celery Worker
After=network.target redis.service boke.service
Wants=redis.service

[Service]
Type=simple
User=boke
Group=boke
WorkingDirectory=/home/boke/BoKe
Environment="PATH=/home/boke/BoKe/venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/home/boke/BoKe/.env
ExecStart=/home/boke/BoKe/venv/bin/celery -A backend.celery_app worker --loglevel=info --concurrency=2
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**使用方法：** 将以上内容分别保存到 `/etc/systemd/system/boke.service` 和 `/etc/systemd/system/boke-celery.service`。记得将 `/home/boke/BoKe` 替换为你的实际项目路径，将 `boke` 替换为你的实际用户名。
