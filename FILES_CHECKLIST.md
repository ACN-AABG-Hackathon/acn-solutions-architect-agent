# 📋 部署文件清单

## ✅ 必需文件(必须上传到 GitHub)

### 核心应用文件
- [ ] `streamlit_app.py` - 主应用入口文件
- [ ] `requirements.txt` - Python 依赖包列表
- [ ] `packages.txt` - 系统依赖包列表
- [ ] `.gitignore` - Git 忽略文件配置

### 代码模块
- [ ] `agents/` - AI 智能体模块
  - [ ] `design_agent.py`
  - [ ] `compare_agent.py`
  - [ ] `diagram_agent.py`
  - [ ] `staffing_agent.py`
  - [ ] `supervisor_agent.py`
  - [ ] `__init__.py`

- [ ] `auth/` - 认证模块
  - [ ] `cognito_auth.py`
  - [ ] `streamlit_auth.py`
  - [ ] `__init__.py`

- [ ] `tools/` - 工具模块
  - [ ] `document_rag.py`
  - [ ] `gateway_client.py`
  - [ ] `memory.py`
  - [ ] `prompt_utils.py`
  - [ ] `refinement_engine.py`
  - [ ] `requirements_formatter.py`
  - [ ] `s3_utils.py`
  - [ ] `system_requirements.py`
  - [ ] `__init__.py`

- [ ] `workflow/` - 工作流模块
  - [ ] `orchestrator.py`
  - [ ] `__init__.py`

### Streamlit 配置
- [ ] `.streamlit/config.toml` - Streamlit 应用配置

### 文档文件(推荐)
- [ ] `README.md` - 项目说明
- [ ] `DEPLOYMENT_GUIDE.md` - 部署指南
- [ ] `QUICK_START.md` - 快速开始指南

---

## ⚠️ 不要上传的文件

### 敏感信息文件
- [ ] ❌ `.env` - 包含敏感信息,不要提交!
- [ ] ❌ `.streamlit/secrets.toml` - 包含敏感信息,不要提交!
- [ ] ❌ 任何包含 AWS 凭证的文件

### 可选模板文件
- [ ] ✅ `.env.example` - 可以上传(仅模板)
- [ ] ✅ `.streamlit/secrets.toml.example` - 可以上传(仅模板)

---

## 📝 Streamlit Cloud 配置清单

### 在 Streamlit Cloud 中需要配置的 Secrets

```toml
# 复制以下内容到 Streamlit Cloud Secrets 编辑器
# 替换所有 YOUR_* 占位符为实际值

AWS_REGION = "us-east-1"
BEDROCK_MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"

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

---

## 🔍 部署前检查

### GitHub 仓库检查
- [ ] 所有必需文件已上传
- [ ] `.env` 文件**没有**被上传
- [ ] `.gitignore` 文件正确配置
- [ ] 仓库可以正常访问

### AWS 服务检查
- [ ] S3 buckets 已创建
- [ ] Cognito User Pool 已配置
- [ ] Cognito App Client 已创建
- [ ] AgentCore Memory 已创建
- [ ] AgentCore Gateway 已配置
- [ ] IAM 权限已正确设置

### Streamlit Cloud 检查
- [ ] 已使用 GitHub 账号登录
- [ ] 已选择正确的仓库和分支
- [ ] Main file path 设置为 `streamlit_app.py`
- [ ] Secrets 已正确配置(所有占位符已替换)
- [ ] Python 版本设置为 3.11

---

## 📊 文件统计

| 类别 | 数量 |
|------|------|
| Python 模块文件 | 18 |
| 配置文件 | 4 |
| 文档文件 | 6 |
| 模板文件 | 2 |
| **总计** | **30** |

---

## ✅ 部署成功标志

部署成功后,你应该能够:
- [ ] 访问应用 URL
- [ ] 看到 Cognito 登录页面
- [ ] 成功登录应用
- [ ] 上传文档
- [ ] 生成设计方案
- [ ] 查看架构图

---

## 🆘 如果遇到问题

1. **检查 Streamlit Cloud 日志**
   - Manage app → Logs
   - 查找红色错误信息

2. **验证 Secrets 配置**
   - 确保所有占位符已替换
   - 检查是否有拼写错误

3. **检查 AWS 服务**
   - 验证所有服务在正确的区域
   - 确认 IAM 权限正确

4. **查阅文档**
   - DEPLOYMENT_GUIDE.md
   - README.md
   - streamlit_cloud_compatibility_check.md

---

**准备好了吗? 开始部署吧! 🚀**
