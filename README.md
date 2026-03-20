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

### 3) 启动前端

新开一个终端：

```bash
cd frontend
npm install
npm run dev
```

前端默认地址：`http://127.0.0.1:5173`

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
