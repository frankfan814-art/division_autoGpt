# 开发环境搭建指南

> Creative AutoGPT 开发环境配置完整教程

## 1. 系统要求

### 1.1 硬件要求

| 组件 | 最低配置 | 推荐配置 |
|------|---------|---------|
| **CPU** | 4核 | 8核+ |
| **内存** | 8GB | 16GB+ |
| **硬盘** | 20GB 可用空间 | 50GB+ SSD |
| **网络** | 稳定互联网连接（访问 LLM API） | - |

### 1.2 软件要求

| 软件 | 版本要求 | 用途 |
|------|---------|------|
| **Python** | 3.10+ | 后端开发 |
| **Node.js** | 18+ | 前端开发 |
| **npm/pnpm** | 最新版 | 包管理 |
| **Git** | 最新版 | 版本控制 |
| **VS Code** | 推荐 | 代码编辑器 |

---

## 2. 后端环境搭建

### 2.1 克隆项目

```bash
# 克隆仓库
git clone https://github.com/your-org/creative-autogpt.git
cd creative-autogpt
```

---

### 2.2 创建 Python 虚拟环境

**macOS/Linux**

```bash
# 使用 venv
python3 -m venv venv
source venv/bin/activate

# 或使用 conda（推荐）
conda create -n creative_autogpt python=3.10
conda activate creative_autogpt
```

**Windows**

```bash
# 使用 venv
python -m venv venv
.\venv\Scripts\activate

# 或使用 conda
conda create -n creative_autogpt python=3.10
conda activate creative_autogpt
```

---

### 2.3 安装依赖

```bash
# 安装核心依赖
pip install -r requirements.txt

# 开发依赖（可选）
pip install -r requirements-dev.txt
```

**requirements.txt 核心依赖说明**

```txt
# Web 框架
fastapi==0.104.1
uvicorn[standard]==0.24.0
websockets==12.0

# LLM 客户端
openai==1.3.5                    # OpenAI 兼容接口
anthropic==0.7.2                 # Claude (可选)
dashscope==1.14.0                # 阿里云通义千问

# 向量数据库
chromadb==0.4.18                 # 向量存储
sentence-transformers==2.2.2     # 文本嵌入

# 数据库
sqlalchemy==2.0.23               # ORM
alembic==1.12.1                  # 数据库迁移

# 工具库
pydantic==2.5.0                  # 数据验证
python-dotenv==1.0.0             # 环境变量
loguru==0.7.2                    # 日志
jinja2==3.1.2                    # 模板引擎
aiofiles==23.2.1                 # 异步文件操作
```

---

### 2.4 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑 .env 文件
nano .env  # 或使用你喜欢的编辑器
```

**.env 配置示例**

```bash
# === 应用配置 ===
APP_ENV=development              # development/production
APP_DEBUG=true
APP_HOST=0.0.0.0
APP_PORT=8000
SECRET_KEY=your-secret-key-here-change-in-production

# === 数据库配置 ===
# 开发环境使用 SQLite
DATABASE_URL=sqlite:///./data/creative_autogpt.db

# 生产环境使用 PostgreSQL
# DATABASE_URL=postgresql://user:password@localhost:5432/creative_autogpt

# === 向量数据库 ===
CHROMA_PERSIST_DIRECTORY=./data/chroma
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2

# === LLM API Keys ===
# 阿里云通义千问 (Qwen)
ALIYUN_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ALIYUN_MODEL=qwen-max

# DeepSeek
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# 火山引擎豆包 (Doubao)
ARK_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ARK_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
ARK_MODEL=doubao-pro-32k

# === LLM 配置 ===
# 是否启用各个模型
ENABLE_QWEN=true
ENABLE_DEEPSEEK=true
ENABLE_DOUBAO=true

# 通用参数
DEFAULT_TEMPERATURE=0.7
DEFAULT_MAX_TOKENS=4000
LLM_REQUEST_TIMEOUT=120          # 秒
MAX_RETRIES=3

# === 存储配置 ===
STORAGE_TYPE=local               # local/s3
LOCAL_STORAGE_PATH=./data/novels

# S3 配置（生产环境）
# S3_BUCKET=creative-autogpt
# S3_REGION=us-east-1
# S3_ACCESS_KEY=xxx
# S3_SECRET_KEY=xxx

# === 日志配置 ===
LOG_LEVEL=DEBUG                  # DEBUG/INFO/WARNING/ERROR
LOG_FILE=./logs/app.log
LOG_ROTATION=1 day
LOG_RETENTION=30 days

# === 性能配置 ===
MAX_CONCURRENT_TASKS=5
WORKER_POOL_SIZE=10

# === 前端配置 ===
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

### 2.5 初始化数据库

```bash
# 创建数据目录
mkdir -p data logs

# 运行数据库迁移
alembic upgrade head

# 或使用项目脚本
python scripts/init_db.py
```

---

### 2.6 运行后端服务

**开发模式（热重载）**

```bash
# 使用 uvicorn
uvicorn src.creative_autogpt.api.main:app --reload --host 0.0.0.0 --port 8000

# 或使用项目脚本
python run_server.py
```

**生产模式**

```bash
# 使用 gunicorn + uvicorn worker
gunicorn src.creative_autogpt.api.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 300
```

**验证服务**

```bash
# 访问 API 文档
open http://localhost:8000/docs

# 测试健康检查
curl http://localhost:8000/health
```

---

## 3. 前端环境搭建

### 3.1 进入前端目录

```bash
cd frontend
```

---

### 3.2 安装依赖

**使用 npm**

```bash
npm install
```

**使用 pnpm（推荐，更快）**

```bash
# 安装 pnpm
npm install -g pnpm

# 安装依赖
pnpm install
```

---

### 3.3 配置环境变量

```bash
# 复制配置
cp .env.example .env.local

# 编辑配置
nano .env.local
```

**.env.local 示例**

```bash
# API 配置
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_WS_URL=ws://localhost:8000/ws

# 应用配置
VITE_APP_TITLE=Creative AutoGPT
VITE_APP_DESCRIPTION=AI 驱动的长篇小说创作系统

# 功能开关
VITE_ENABLE_ANALYTICS=false
VITE_ENABLE_DEBUG=true
```

---

### 3.4 运行前端服务

**开发模式**

```bash
# 使用 npm
npm run dev

# 使用 pnpm
pnpm dev

# 访问
open http://localhost:5173
```

**构建生产版本**

```bash
# 构建
npm run build

# 预览构建结果
npm run preview
```

---

## 4. IDE 配置

### 4.1 VS Code 配置

**推荐插件**

```json
{
  "recommendations": [
    // Python
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    
    // JavaScript/TypeScript
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "bradlc.vscode-tailwindcss",
    
    // 通用
    "eamodio.gitlens",
    "editorconfig.editorconfig",
    "gruntfuggly.todo-tree",
    "yzhang.markdown-all-in-one"
  ]
}
```

**settings.json**

```json
{
  // Python
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": true,
  
  // TypeScript
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.fixAll.eslint": true
  },
  "eslint.validate": ["javascript", "typescript", "javascriptreact", "typescriptreact"],
  
  // 通用
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "**/node_modules": true
  }
}
```

---

### 4.2 PyCharm 配置

1. **打开项目**：File → Open → 选择项目目录
2. **配置解释器**：Settings → Project → Python Interpreter → 选择 venv
3. **配置代码风格**：Settings → Editor → Code Style → Python → Black
4. **启用类型检查**：Settings → Editor → Inspections → Python → Type Checker

---

## 5. 开发工具

### 5.1 代码质量工具

**安装开发依赖**

```bash
pip install black pylint mypy pytest pytest-cov
```

**使用方式**

```bash
# 格式化代码
black src/

# 代码检查
pylint src/

# 类型检查
mypy src/

# 运行测试
pytest tests/ -v

# 测试覆盖率
pytest tests/ --cov=src --cov-report=html
```

---

### 5.2 Git Hooks（推荐）

**安装 pre-commit**

```bash
pip install pre-commit

# 安装 hooks
pre-commit install
```

**.pre-commit-config.yaml**

```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files

  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/pylint
    rev: v3.0.2
    hooks:
      - id: pylint
        args: [--max-line-length=120]
```

---

## 6. Docker 部署（可选）

### 6.1 使用 Docker Compose

**docker-compose.yml**

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - APP_ENV=production
      - DATABASE_URL=postgresql://postgres:password@db:5432/creative_autogpt
    env_file:
      - .env
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    depends_on:
      - db
      - redis

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "80:80"
    depends_on:
      - backend

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=creative_autogpt
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
```

**启动服务**

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f backend

# 停止服务
docker-compose down
```

---

## 7. 常见问题

### 7.1 依赖安装失败

**问题**：`pip install` 失败

**解决方案**：

```bash
# 升级 pip
pip install --upgrade pip setuptools wheel

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

---

### 7.2 向量数据库初始化失败

**问题**：ChromaDB 初始化错误

**解决方案**：

```bash
# 删除旧数据
rm -rf ./data/chroma

# 重新初始化
python scripts/init_vector_db.py
```

---

### 7.3 LLM API 调用失败

**问题**：LLM 调用超时或失败

**检查清单**：

1. ✅ API Key 是否正确
2. ✅ 网络是否可访问 API 地址
3. ✅ API 配额是否充足
4. ✅ 模型名称是否正确

**测试脚本**

```python
# scripts/test_llm.py
from dotenv import load_dotenv
import os
from openai import OpenAI

load_dotenv()

# 测试 DeepSeek
client = OpenAClient(
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url=os.getenv("DEEPSEEK_BASE_URL")
)

response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[{"role": "user", "content": "你好"}]
)

print(response.choices[0].message.content)
```

---

### 7.4 端口被占用

**问题**：`Address already in use`

**解决方案**：

```bash
# macOS/Linux - 查找占用端口的进程
lsof -i :8000

# 终止进程
kill -9 <PID>

# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# 或使用其他端口
uvicorn main:app --port 8001
```

---

## 8. 下一步

环境搭建完成后：

1. 📖 阅读 [快速入门指南](./QUICKSTART.md)
2. 🏗️ 了解 [架构总览](../architecture/OVERVIEW.md)
3. 🔧 查看 [API 文档](../api/REST_API.md)
4. 💡 尝试 [示例项目](../../examples/)

---

## 9. 获取帮助

- 📚 [完整文档](../README.md)
- 🐛 [提交 Issue](https://github.com/your-org/creative-autogpt/issues)
- 💬 [加入讨论](https://github.com/your-org/creative-autogpt/discussions)

---

*版本: 1.0*  
*最后更新: 2026-01-23*
