# 🚀 快速开始 - 5分钟部署到 Streamlit Cloud

## 📋 准备工作(2分钟)

### 1. 下载修复后的项目
你已经有了修复后的项目压缩包: `aws-solutions-architect-agent-v5-streamlit-ready.zip`

### 2. 准备 GitHub 账号
- 访问 [github.com](https://github.com) 并登录
- 如果没有账号,先注册一个

### 3. 准备 Streamlit Cloud 账号
- 访问 [share.streamlit.io](https://share.streamlit.io)
- 使用 GitHub 账号登录(会自动授权)

---

## 🎯 部署步骤(3分钟)

### 步骤 1: 创建 GitHub 仓库

1. 在 GitHub 点击右上角 "+" → "New repository"
2. 填写信息:
   - **Repository name**: `aws-architect-agent` (或其他名称)
   - **Visibility**: Private (推荐) 或 Public
   - **不要**勾选 "Add a README file"
3. 点击 "Create repository"

### 步骤 2: 上传代码到 GitHub

#### 方法 A: 使用 GitHub Web 界面(推荐,最简单)

1. 解压 `aws-solutions-architect-agent-v5-streamlit-ready.zip`
2. 在刚创建的 GitHub 仓库页面,点击 "uploading an existing file"
3. 拖拽所有文件和文件夹到上传区域
4. 在底部填写 commit 信息: "Initial commit"
5. 点击 "Commit changes"

#### 方法 B: 使用 Git 命令行

```bash
# 解压项目
unzip aws-solutions-architect-agent-v5-streamlit-ready.zip
cd aws-solutions-architect-agent-v5-streamlit-ready

# 初始化 Git
git init
git add .
git commit -m "Initial commit"

# 关联远程仓库(替换为你的仓库 URL)
git remote add origin https://github.com/your-username/aws-architect-agent.git
git branch -M main
git push -u origin main
```

### 步骤 3: 部署到 Streamlit Cloud

1. 访问 [share.streamlit.io](https://share.streamlit.io)
2. 点击 "New app"
3. 填写配置:
   - **Repository**: 选择刚创建的仓库
   - **Branch**: main
   - **Main file path**: `streamlit_app.py`
4. 点击 "Advanced settings..."
5. 在 **Secrets** 区域粘贴以下内容(⚠️ 需要替换为你的实际值):

```toml
AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

# 替换为你的实际值
DESIGN_KB_ID = "YOUR_DESIGN_KB_ID"
ARCHITECTURE_KB_ID = "YOUR_ARCHITECTURE_KB_ID"
DIAGRAM_KB_ID = "YOUR_DIAGRAM_KB_ID"

S3_BUCKET_NAME = "your-bucket-name"
S3_RESULT_BUCKET_NAME = "your-results-bucket"
S3_DIAGRAM_PREFIX = "architecture-diagrams/"

PORT = 8080
LOG_LEVEL = "INFO"

AGENTCORE_MEMORY_ENABLED = true
AGENTCORE_SESSION_TTL = 3600
AGENTCORE_MEMORY_ID = "YOUR_MEMORY_ID"

DIAGRAM_RENDER_METHOD = "kroki"

AGENTCORE_GATEWAY_ID = "YOUR_GATEWAY_ID"
AGENTCORE_GATEWAY_URL = "https://your-gateway-url.amazonaws.com/mcp"
AGENTCORE_ACCESS_TOKEN = "YOUR_NEW_ACCESS_TOKEN"

COGNITO_USER_POOL_ID = "YOUR_USER_POOL_ID"
COGNITO_CLIENT_ID = "YOUR_CLIENT_ID"
COGNITO_CLIENT_SECRET = "YOUR_CLIENT_SECRET"
```

6. 点击 "Deploy!"

---

## ⏱️ 等待部署(2-5分钟)

部署过程中你会看到:
1. ⏳ "Installing dependencies..." (安装依赖)
2. ⏳ "Building app..." (构建应用)
3. ✅ "Your app is live!" (部署成功)

---

## ✅ 验证部署

### 1. 访问应用
点击 Streamlit Cloud 提供的 URL,例如: `https://your-app.streamlit.app`

### 2. 测试登录
- 应该看到 Cognito 登录页面
- 使用你的 Cognito 账号登录

### 3. 测试功能
- 上传一个测试文档
- 验证 AI 功能是否正常

---

## ⚠️ 如果部署失败

### 查看错误日志
1. 在 Streamlit Cloud 应用页面
2. 点击 "Manage app"
3. 查看 "Logs" 标签
4. 查找红色错误信息

### 常见错误和解决方案

#### 错误 1: `ModuleNotFoundError`
**原因**: 某个依赖包安装失败
**解决方案**:
1. 在 GitHub 仓库中编辑 `requirements.txt`
2. 将 `requirements_streamlit_cloud.txt` 的内容复制过去
3. Commit 更改,Streamlit 会自动重新部署

#### 错误 2: `Unable to locate credentials`
**原因**: AWS 凭证配置不正确
**解决方案**:
1. 在 Streamlit Cloud 应用设置中检查 Secrets
2. 确认所有 AWS 相关的配置都已填写
3. 如果使用 IAM Role,确保配置正确

#### 错误 3: `COGNITO_USER_POOL_ID not set`
**原因**: Cognito 配置缺失
**解决方案**:
1. 在 Streamlit Cloud Secrets 中添加 Cognito 配置
2. 确保 User Pool ID、Client ID、Client Secret 都正确

---

## 🔑 获取配置值的方法

### AWS S3 Bucket
```bash
# 创建 S3 buckets
aws s3 mb s3://your-bucket-name --region us-east-1
aws s3 mb s3://your-results-bucket --region us-east-1
```

### AWS Cognito
1. 打开 [AWS Cognito 控制台](https://console.aws.amazon.com/cognito)
2. 创建 User Pool → 记录 User Pool ID
3. 创建 App Client → 记录 Client ID 和 Client Secret

### AgentCore Memory
1. 打开 [AWS Bedrock 控制台](https://console.aws.amazon.com/bedrock)
2. 导航到 "Memory" → 创建新 Memory
3. 记录 Memory ID

### AgentCore Gateway
1. 在 Bedrock 控制台导航到 "Gateways"
2. 创建新 Gateway → 记录 Gateway ID 和 URL
3. 生成 Access Token

---

## 📚 更多帮助

如果需要更详细的说明,请查看:
- **DEPLOYMENT_GUIDE.md** - 完整部署指南
- **README.md** - 项目说明
- **streamlit_cloud_compatibility_check.md** - 兼容性问题详情

---

## 🎉 完成!

如果一切顺利,你的应用现在应该已经在运行了!

**应用 URL**: `https://your-app.streamlit.app`

享受你的 AWS Solutions Architect Agent! ☁️
