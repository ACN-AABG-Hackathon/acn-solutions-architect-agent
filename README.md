# AWS Solutions Architect Agent v5

一个基于多智能体架构的 AWS 解决方案设计助手,集成了文档处理、架构设计、方案对比、图表生成等功能。

## 功能特性

- 📄 **文档上传与查询**: 支持 PDF、DOCX、TXT 格式的需求文档上传
- 🏗️ **多方案设计**: 基于 AWS Well-Architected Framework 生成多个架构方案
- 📊 **方案对比**: 自动对比不同方案的优缺点
- 🎨 **架构图生成**: 自动生成 AWS 架构图
- 👥 **人员配置**: 生成项目人员和时间线规划
- 🔐 **AWS Cognito 认证**: 集成用户认证和授权

## 技术栈

- **前端**: Streamlit
- **AI 框架**: Strands Agents, LangGraph, LangChain
- **云服务**: AWS Bedrock, S3, Cognito, AgentCore
- **文档处理**: PyPDF, python-docx, Docling
- **数据模型**: Pydantic

## 部署到 Streamlit Cloud

### 前置要求

1. **GitHub 账号**: 用于托管代码
2. **Streamlit Cloud 账号**: 在 [share.streamlit.io](https://share.streamlit.io) 注册
3. **AWS 账号**: 配置 Bedrock、S3、Cognito 等服务

### 步骤 1: 准备 GitHub 仓库

1. 在 GitHub 创建新仓库
2. 克隆仓库到本地:
   ```bash
   git clone https://github.com/your-username/your-repo.git
   cd your-repo
   ```

3. 复制项目文件到仓库:
   ```bash
   # 复制所有必要文件
   cp -r agents/ auth/ tools/ workflow/ your-repo/
   cp streamlit_app.py requirements.txt packages.txt .gitignore your-repo/
   cp -r .streamlit/ your-repo/
   ```

4. 提交并推送:
   ```bash
   git add .
   git commit -m "Initial commit"
   git push origin main
   ```

### 步骤 2: 配置 AWS 服务

#### 2.1 配置 IAM Role (推荐)

为 Streamlit Cloud 创建 IAM Role,而不是使用硬编码的 Access Key:

1. 在 AWS IAM 控制台创建新角色
2. 添加以下权限策略:
   - `AmazonBedrockFullAccess`
   - `AmazonS3FullAccess` (或自定义策略限制到特定 bucket)
   - `AmazonCognitoPowerUser`

3. 配置信任关系以允许外部访问

#### 2.2 配置 S3 Buckets

创建两个 S3 buckets:
- `aws-architect-agent-documents`: 存储上传的文档
- `aws-architect-agent-results`: 存储生成的结果和图表

#### 2.3 配置 AWS Cognito

1. 创建 User Pool
2. 创建 App Client
3. 记录以下信息:
   - User Pool ID
   - Client ID
   - Client Secret

#### 2.4 配置 AgentCore Memory

1. 在 AWS Bedrock 控制台创建 Memory 资源
2. 记录 Memory ID

#### 2.5 配置 AgentCore Gateway

1. 创建 Gateway 资源
2. 记录 Gateway ID 和 URL
3. 生成 Access Token

### 步骤 3: 配置 Streamlit Cloud Secrets

1. 登录 [Streamlit Cloud](https://share.streamlit.io)
2. 选择你的应用
3. 点击 "Settings" → "Secrets"
4. 添加以下配置:

```toml
# AWS Configuration
AWS_REGION = "us-east-1"

# 如果使用 IAM Role,不需要配置以下两项
# AWS_ACCESS_KEY_ID = "your-access-key-id"
# AWS_SECRET_ACCESS_KEY = "your-secret-key"

# Bedrock Configuration
BEDROCK_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# Knowledge Base IDs
DESIGN_KB_ID = "YOUR_DESIGN_KB_ID"
ARCHITECTURE_KB_ID = "YOUR_ARCHITECTURE_KB_ID"
DIAGRAM_KB_ID = "YOUR_DIAGRAM_KB_ID"

# S3 Configuration
S3_BUCKET_NAME = "aws-architect-agent-documents"
S3_RESULT_BUCKET_NAME = "aws-architect-agent-results"
S3_DIAGRAM_PREFIX = "architecture-diagrams/"

# Application Configuration
PORT = 8080
LOG_LEVEL = "INFO"

# AgentCore Configuration
AGENTCORE_MEMORY_ENABLED = true
AGENTCORE_SESSION_TTL = 3600
AGENTCORE_MEMORY_ID = "YOUR_MEMORY_ID"

# Diagram Rendering Method
DIAGRAM_RENDER_METHOD = "kroki"

# AgentCore Gateway Configuration
AGENTCORE_GATEWAY_ID = "YOUR_GATEWAY_ID"
AGENTCORE_GATEWAY_URL = "https://your-gateway-url.amazonaws.com/mcp"
AGENTCORE_ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"

# AWS Cognito Configuration
COGNITO_USER_POOL_ID = "YOUR_USER_POOL_ID"
COGNITO_CLIENT_ID = "YOUR_CLIENT_ID"
COGNITO_CLIENT_SECRET = "YOUR_CLIENT_SECRET"
```

### 步骤 4: 部署应用

1. 在 Streamlit Cloud 点击 "New app"
2. 选择你的 GitHub 仓库
3. 设置:
   - **Main file path**: `streamlit_app.py`
   - **Python version**: 3.11
4. 点击 "Deploy"

### 步骤 5: 验证部署

1. 等待部署完成(通常需要 5-10 分钟)
2. 访问应用 URL
3. 使用 Cognito 账号登录
4. 测试文档上传和方案生成功能

## 本地开发

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置环境变量

复制 `.streamlit/secrets.toml.example` 到 `.streamlit/secrets.toml` 并填入你的配置:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

或者使用 `.env` 文件:

```bash
cp .env.example .env
# 编辑 .env 文件填入配置
```

### 运行应用

```bash
streamlit run streamlit_app.py
```

应用将在 `http://localhost:8501` 启动。

## 故障排查

### 问题 1: 依赖安装失败

**原因**: 某些依赖包可能不在 PyPI 上或需要特殊配置

**解决方案**:
- 检查 `requirements.txt` 中的包是否都可用
- 尝试使用 `requirements_streamlit_cloud.txt` (已移除问题依赖)
- 联系包维护者或使用替代方案

### 问题 2: AWS 认证失败

**原因**: IAM 权限配置不正确或凭证过期

**解决方案**:
- 验证 IAM Role 权限
- 检查 Streamlit Secrets 中的配置
- 确保 AWS 服务在正确的 region

### 问题 3: Cognito 认证失败

**原因**: Cognito 配置不正确或回调 URL 未设置

**解决方案**:
- 在 Cognito App Client 中添加应用 URL 到回调 URL
- 检查 User Pool 和 Client ID 是否正确
- 验证 Client Secret (如果使用)

### 问题 4: AgentCore Gateway 调用失败

**原因**: Access Token 过期或 Gateway URL 不正确

**解决方案**:
- 重新生成 Access Token
- 验证 Gateway URL 格式
- 检查网络连接和防火墙设置

### 问题 5: 系统依赖缺失

**原因**: `packages.txt` 中的系统库未正确安装

**解决方案**:
- 检查 Streamlit Cloud 日志
- 验证 `packages.txt` 中的包名是否正确
- 尝试移除不必要的依赖

## 安全最佳实践

1. **不要提交敏感信息到 Git**:
   - 使用 `.gitignore` 排除 `.env` 和 `secrets.toml`
   - 定期检查 Git 历史

2. **使用 IAM Role 而非硬编码凭证**:
   - 在生产环境使用 IAM Role
   - 避免在代码中硬编码 Access Key

3. **定期轮换凭证**:
   - 定期更新 Access Token
   - 轮换 Cognito Client Secret

4. **最小权限原则**:
   - IAM 策略只授予必要权限
   - 限制 S3 bucket 访问范围

## 项目结构

```
.
├── agents/                 # AI 智能体
│   ├── design_agent.py    # 设计方案生成
│   ├── compare_agent.py   # 方案对比
│   ├── diagram_agent.py   # 架构图生成
│   └── staffing_agent.py  # 人员配置
├── auth/                   # 认证模块
│   ├── cognito_auth.py    # Cognito 认证
│   └── streamlit_auth.py  # Streamlit 认证集成
├── tools/                  # 工具模块
│   ├── document_rag.py    # 文档 RAG
│   ├── gateway_client.py  # Gateway 客户端
│   ├── memory.py          # 记忆管理
│   └── s3_utils.py        # S3 工具
├── workflow/               # 工作流
│   └── orchestrator.py    # 编排器
├── ui/                     # UI (原始位置)
│   └── streamlit_app.py   # Streamlit 应用
├── .streamlit/             # Streamlit 配置
│   ├── config.toml        # 应用配置
│   └── secrets.toml.example  # Secrets 模板
├── streamlit_app.py        # 主应用入口
├── requirements.txt        # Python 依赖
├── packages.txt            # 系统依赖
├── .gitignore             # Git 忽略文件
└── README.md              # 本文件
```

## 贡献

欢迎提交 Issue 和 Pull Request!

## 许可证

[MIT License](LICENSE)

## 联系方式

如有问题,请联系: [your-email@example.com]
