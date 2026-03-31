# Online Exam System

一个可直接运行的在线考试系统，前后端分离：
- 后端：Django + DRF + SQLite
- 前端：Vue 3 + Vite

## 功能概览

- 用户与角色：学生 / 老师注册登录
- 老师端：课程管理、题库管理、试卷管理、阅卷与成绩发布
- 学生端：参加考试、查看成绩
- 阅卷：支持单选题与主观题，主观题人工评分，统一发布成绩

## 项目结构

- `backend/` Django 项目
- `frontend/` Vue 项目

## 环境要求

- Python 3.10+
- Node.js 18+
- npm 9+

## 快速启动

### 1) 克隆项目

```bash
git clone <your-repo-url>
cd "Online Exam System"
```

### 2) 启动后端

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r ..\requirements.txt
python manage.py migrate
python manage.py runserver
```

后端默认地址：`http://127.0.0.1:8000`

如需启用邮箱验证码（找回密码 / 绑定邮箱），请先配置 SMTP 环境变量：

```bash
# Windows PowerShell 示例（126邮箱）
$env:EMAIL_HOST="smtp.126.com"
$env:EMAIL_PORT="465"
$env:EMAIL_USE_SSL="true"
$env:EMAIL_USE_TLS="false"
$env:EMAIL_HOST_USER="你的发件邮箱"
$env:EMAIL_HOST_PASSWORD="你的SMTP授权码"
$env:DEFAULT_FROM_EMAIL="你的发件邮箱"
```

说明：
- 126 邮箱常用 `SSL + 465`。
- 若你的邮箱服务商要求 `TLS + 587`，改为 `EMAIL_USE_SSL=false`、`EMAIL_USE_TLS=true` 即可。

### 3) 启动前端

新开一个终端：

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：`http://127.0.0.1:5173`

### 4) 局域网联机测试（CMD 一键）

在项目根目录执行：

```bat
start-lan.cmd
```

如果自动识别 IP 异常，可手动指定：

```bat
start-lan.cmd 192.168.1.10
```

脚本会自动：
- 检测本机局域网 IP
- 启动后端（`0.0.0.0:8000`）
- 启动前端（`0.0.0.0:5173`）
- 把前端 API 地址自动设为 `http://你的IP:8000/api`

局域网同学访问：
- 前端：`http://你的IP:5173`

脚本文件：
- 根目录启动器：`start-lan.cmd`
- 后端脚本：`backend/start-lan-backend.cmd`
- 前端脚本：`frontend/start-lan-frontend.cmd`

若他人仍无法访问：
- 确认在同一 Wi-Fi / 同一网段。
- 允许 Windows 防火墙放行端口 `8000`、`5173`。
- 路由器关闭 AP 隔离（客户端隔离）。

## 常用命令

### 后端

```bash
cd backend
python manage.py check
python manage.py makemigrations
python manage.py migrate
```

### 前端

```bash
cd frontend
npm run dev
npm run build
```

## 主要接口（节选）

- `POST /api/auth/register/`
- `POST /api/auth/login/`
- `GET /api/auth/me/`
- `POST /api/auth/password-reset/send-code/`
- `POST /api/auth/password-reset/confirm/`
- `POST /api/auth/email/send-bind-code/`
- `POST /api/auth/email/bind/`
- `GET|POST /api/exams/`
- `GET /api/exams/{id}/`
- `POST /api/exams/{id}/submit/`
- `GET /api/exams/{id}/submissions/`
- `POST /api/submissions/{id}/grade/`
- `POST /api/exams/{id}/release-results/`
- `GET /api/submissions/mine/`

## 提交到 GitHub 建议

```bash
git init
git add .
git commit -m "feat: online exam system"
git branch -M main
git remote add origin <your-repo-url>
git push -u origin main
```

如果你是已存在仓库，跳过 `git init`，直接从 `git add .` 开始。
