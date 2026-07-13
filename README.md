# AI agent 数据分析

基于 **OpenAI Agents SDK** 的数据分析 Web 产品：Planner → Builder → Verifier 三智能体流水线。前端与后端同仓，可一键部署到 [Render](https://dashboard.render.com/)。

## 功能

- 商务风格单页：配置 API、输入问题、查看过程与报告
- 历史任务与 API 配置保存在浏览器 `localStorage`（本机，服务端不落库）
- 兼容任意 OpenAI 兼容 API（OpenAI / DeepSeek / 通义千问等）
- Builder 使用内置近 12 个月销售样例数据（月度 / 品类 / 区域）
- Verifier 对照接受标准验证，前端明确展示通过 / 未通过

## 本地运行

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

打开 http://127.0.0.1:8000

## 一键部署到 Render

1. 将本仓库推送到 GitHub
2. 打开 [Render Dashboard](https://dashboard.render.com/) → **New** → **Blueprint**
3. 选择该仓库，识别 `render.yaml` 后创建服务
4. 或手动 **New Web Service**：
   - Runtime: Python
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Health Check Path: `/api/health`

部署完成后，在页面右上角配置你的 API 地址、Key、模型即可使用。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/sample-data` | 查看内置销售样例 |
| POST | `/api/test-connection` | 测试 LLM 连通性 |
| POST | `/api/analyze` | SSE 流式分析过程 |

分析请求体（前端从 localStorage 读取后随请求发送，服务端不持久化 Key）：

```json
{
  "question": "最近半年销售情况怎么样？",
  "api_base": "https://api.openai.com/v1",
  "api_key": "sk-...",
  "model": "gpt-4o-mini"
}
```

## 智能体流程

1. **PlannerAgent**：拆解任务、定义接受标准  
2. **BuilderAgent**：调用 `fetch_sales_data` 取内置数据并生成报告  
3. **VerifierAgent**：按接受标准逐条验证，输出通过/未通过最终报告  
