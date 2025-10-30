# Streamlit Cloud 部署快速指南

## 🚀 快速开始(5分钟部署)

### 第 1 步: 准备 GitHub 仓库

```bash
# 1. 在 GitHub 创建新仓库(例如: aws-architect-agent)

# 2. 克隆到本地
git clone https://github.com/your-username/aws-architect-agent.git
cd aws-architect-agent

# 3. 复制项目文件
# 将以下文件/文件夹复制到仓库根目录:
# - agents/
# - auth/
# - tools/
# - workflow/
# - .streamlit/
# - streamlit_app.py
# - requirements.txt (或 requirements_streamlit_cloud.txt)
# - packages.txt
# - .gitignore
# - README.md

# 4. 提交并推送
git add .
git commit -m "Initial deployment"
git push origin main
```

### 第 2 步: 部署到 Streamlit Cloud

1. 访问 [share.streamlit.io](https://share.streamlit.io)
2. 使用 GitHub 账号登录
3. 点击 "New app"
4. 填写配置:
   - **Repository**: 选择你的仓库
   - **Branch**: main
   - **Main file path**: `streamlit_app.py`
   - **Python version**: 3.11
5. 点击 "Advanced settings"
6. 在 "Secrets" 中粘贴配置(见下文)
7. 点击 "Deploy"

### 第 3 步: 配置 Secrets

在 Streamlit Cloud 的 Secrets 编辑器中粘贴以下内容(替换为你的实际值):

```toml
# AWS Configuration
AWS_REGION = "us-east-1"

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

---

## 📋 部署前检查清单

### 必须完成的配置

- [ ] 创建 GitHub 仓库并推送代码
- [ ] 创建 AWS S3 buckets (documents 和 results)
- [ ] 配置 AWS Cognito User Pool 和 App Client
- [ ] 创建 AgentCore Memory 资源
- [ ] 创建 AgentCore Gateway 资源
- [ ] 在 Streamlit Cloud 配置所有 Secrets
- [ ] 验证 IAM 权限配置正确

### 可选配置

- [ ] 配置自定义域名
- [ ] 设置 GitHub Actions CI/CD
- [ ] 配置监控和日志
- [ ] 设置备份策略

---

## 🔧 AWS 服务配置详细步骤

### 1. 创建 S3 Buckets

```bash
# 使用 AWS CLI 创建 buckets
aws s3 mb s3://aws-architect-agent-documents --region us-east-1
aws s3 mb s3://aws-architect-agent-results --region us-east-1

# 配置 CORS (如果需要直接从浏览器上传)
aws s3api put-bucket-cors --bucket aws-architect-agent-documents \
  --cors-configuration file://cors-config.json
```

**cors-config.json**:
```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["https://your-app.streamlit.app"],
      "AllowedMethods": ["GET", "PUT", "POST"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3000
    }
  ]
}
```

### 2. 配置 AWS Cognito

#### 创建 User Pool

1. 打开 AWS Cognito 控制台
2. 点击 "Create user pool"
3. 配置:
   - **Sign-in options**: Email
   - **Password policy**: 根据需求设置
   - **MFA**: 可选
   - **User account recovery**: Email
4. 创建完成后记录 **User Pool ID**

#### 创建 App Client

1. 在 User Pool 中点击 "App clients"
2. 点击 "Create app client"
3. 配置:
   - **App client name**: aws-architect-agent
   - **Authentication flows**: ALLOW_USER_PASSWORD_AUTH
   - **Generate client secret**: 是
4. 创建完成后记录 **Client ID** 和 **Client Secret**

#### 配置回调 URL

1. 在 App Client 设置中添加:
   - **Callback URLs**: `https://your-app.streamlit.app`
   - **Sign-out URLs**: `https://your-app.streamlit.app`

### 3. 配置 AgentCore Memory

1. 打开 AWS Bedrock 控制台
2. 导航到 "Memory" 部分
3. 点击 "Create memory"
4. 配置:
   - **Name**: CloudSmithMemory
   - **Description**: Memory for AWS Architect Agent
   - **TTL**: 3600 seconds
5. 创建完成后记录 **Memory ID**

### 4. 配置 AgentCore Gateway

1. 在 AWS Bedrock 控制台导航到 "Gateways"
2. 点击 "Create gateway"
3. 配置:
   - **Name**: cloudsmith-tools-gateway
   - **Type**: MCP
4. 创建完成后:
   - 记录 **Gateway ID**
   - 记录 **Gateway URL**
   - 生成并记录 **Access Token**

### 5. 配置 IAM 权限

创建 IAM 策略(最小权限原则):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream"
      ],
      "Resource": "arn:aws:bedrock:*::foundation-model/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:ListBucket"
      ],
      "Resource": [
        "arn:aws:s3:::aws-architect-agent-documents/*",
        "arn:aws:s3:::aws-architect-agent-results/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "cognito-idp:AdminGetUser",
        "cognito-idp:AdminInitiateAuth"
      ],
      "Resource": "arn:aws:cognito-idp:*:*:userpool/*"
    }
  ]
}
```

---

## 🐛 常见问题排查

### 问题 1: 应用启动失败

**错误信息**: `ModuleNotFoundError: No module named 'xxx'`

**解决方案**:
1. 检查 `requirements.txt` 中是否包含该模块
2. 如果是私有包,考虑使用替代方案
3. 查看 Streamlit Cloud 日志获取详细错误信息

### 问题 2: AWS 认证失败

**错误信息**: `Unable to locate credentials`

**解决方案**:
1. 确认 Streamlit Secrets 中配置了 AWS 凭证或 IAM Role
2. 检查 AWS Region 是否正确
3. 验证 IAM 权限是否充足

### 问题 3: Cognito 登录失败

**错误信息**: `Invalid redirect URI`

**解决方案**:
1. 在 Cognito App Client 中添加应用 URL 到回调 URL 列表
2. 确保 URL 完全匹配(包括 https://)
3. 检查 Client ID 和 Secret 是否正确

### 问题 4: 文件上传失败

**错误信息**: `Access Denied` 或 `CORS error`

**解决方案**:
1. 检查 S3 bucket 权限
2. 配置 CORS 规则
3. 验证 IAM 策略允许 S3 操作

### 问题 5: 系统依赖缺失

**错误信息**: `error while loading shared libraries`

**解决方案**:
1. 检查 `packages.txt` 是否包含所需的系统库
2. 参考 Streamlit Cloud 支持的包列表
3. 考虑使用纯 Python 替代方案

---

## 📊 部署后验证

### 功能测试清单

1. **认证测试**
   - [ ] 能够正常登录
   - [ ] 登出功能正常
   - [ ] Session 持久化正常

2. **文档上传测试**
   - [ ] 能够上传 PDF 文件
   - [ ] 能够上传 DOCX 文件
   - [ ] 文件正确保存到 S3

3. **AI 功能测试**
   - [ ] 设计方案生成正常
   - [ ] 方案对比功能正常
   - [ ] 架构图生成正常
   - [ ] 人员配置生成正常

4. **性能测试**
   - [ ] 页面加载速度 < 3秒
   - [ ] AI 响应时间合理
   - [ ] 无明显卡顿

---

## 🔄 更新部署

### 方法 1: 通过 Git 推送

```bash
# 修改代码后
git add .
git commit -m "Update: description of changes"
git push origin main

# Streamlit Cloud 会自动检测并重新部署
```

### 方法 2: 手动重启

1. 登录 Streamlit Cloud
2. 选择你的应用
3. 点击 "Reboot app"

### 方法 3: 更新 Secrets

1. 在 Streamlit Cloud 应用设置中
2. 点击 "Secrets"
3. 修改配置
4. 保存后应用会自动重启

---

## 📈 监控和维护

### 查看日志

1. 在 Streamlit Cloud 应用页面
2. 点击 "Manage app"
3. 查看 "Logs" 标签

### 监控指标

- **应用可用性**: 定期访问应用检查
- **错误率**: 查看日志中的错误信息
- **响应时间**: 监控 AI 调用延迟
- **资源使用**: 检查内存和 CPU 使用情况

### 定期维护任务

- [ ] 每周检查应用日志
- [ ] 每月更新依赖包
- [ ] 每季度轮换 AWS 凭证
- [ ] 定期备份重要数据

---

## 🔐 安全建议

1. **不要在代码中硬编码凭证**
   - 使用 Streamlit Secrets
   - 使用 AWS IAM Role

2. **定期轮换凭证**
   - Access Token
   - Cognito Client Secret
   - AWS Access Keys

3. **最小权限原则**
   - IAM 策略只授予必要权限
   - 限制 S3 bucket 访问范围

4. **启用审计日志**
   - CloudTrail 记录 AWS API 调用
   - Cognito 用户活动日志

5. **数据加密**
   - S3 启用服务器端加密
   - 传输层使用 HTTPS

---

## 📞 获取帮助

- **Streamlit 文档**: https://docs.streamlit.io
- **AWS 文档**: https://docs.aws.amazon.com
- **GitHub Issues**: 在项目仓库提交 Issue
- **社区支持**: Streamlit Community Forum

---

## ✅ 部署成功!

如果一切顺利,你的应用现在应该已经在 Streamlit Cloud 上运行了!

访问你的应用 URL: `https://your-app.streamlit.app`

享受你的 AWS Solutions Architect Agent! 🎉
