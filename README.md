# 王者荣耀账号筛选/评估 Agent

基于 FastAPI + LangGraph Plan-Execute-Replan 架构的螃蟹平台王者荣耀账号性价比评估工具。支持规则引擎评分 + LLM 复核双管线，内置皮肤质量评分体系，提供 Web 端 SSE 流式交互和用户自定义规则管理。

---

## 功能概览

- **单账号评估**：输入商品链接或详情文案，提取核心字段并给出推荐级别、合理价、共号/出租适配度
- **列表页批量筛选**：输入螃蟹平台列表页 URL，自动抓取候选账号，逐个评分排序后生成排名报告
- **LLM 模型复核**：在规则评分基础上调用 LLM 分析矛盾、排除不适合出租的便宜号、给出购买策略
- **皮肤质量评分**：内置 63 款高分/低分皮肤对照表（典藏/无双/珍品传说/传说），自动识别弱款并影响估值
- **用户系统**：登录/注册，每人可保存自己的评估规则，登录后自动加载，LLM 评估时注入自定义规则
- **SSE 流式输出**：前端实时展示执行计划、步骤进度、LLM 逐 token 生成和最终报告

---

## 基准线

默认以朋友给出的好号标准作为评估基准：

| 指标 | 值 |
|---|---|
| 价格 | 1300 元 |
| 荣耀典藏 | 3 |
| 无双限定 | 3 |
| 珍品传说 | 2 |
| 传说 | 30 |
| 总皮肤 | ~400 |

Agent 会输出：价格合理性、各项差距、达标情况、共号/出租变现适配度、合理价与最高建议买入价、推荐级别、排序分。

---

## 快速启动

### 环境要求

- Python 3.11+
- MySQL（本地，root:root，端口 3306）
- Chrome 浏览器（列表页抓取时需要，路径 `C:\Program Files\Google\Chrome\Application\chrome.exe`）

### 安装

```powershell
# 克隆或进入项目目录
cd "path/to/honor-account-evaluator"

# 安装依赖
pip install -e .
```

### 配置模型

在项目根目录创建 `.env`（参考 `.env.example`）：

```env
# OpenAI 兼容模式
OPENAI_API_KEY=你的 key
OPENAI_BASE_URL=https://api.deepseek.com
OPENAI_MODEL=deepseek-v4-pro

# 或阿里 DashScope
#DASHSCOPE_API_KEY=你的 key
#DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
#DASHSCOPE_MODEL=qwen-plus
```

未配置 key 时，评估会退回到纯规则引擎模式。

### 启动

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 9910
```

首次启动时会自动创建数据库 `honor_evaluator` 及所需表。然后打开浏览器访问：

```
http://127.0.0.1:9910
```

无登录状态会自动跳转到登录/注册页。注册后即可使用完整功能。

---

## 评估管线

```
用户输入 (EvaluateRequest)
  │
  ▼
Planner ── 分析 URL 类型，制定执行计划
  │
  ▼
Executor ── 按计划逐步执行：
  ├─ 抓取列表页 / 读取商品链接
  ├─ 正则提取核心字段（售价、典藏、无双、传说、皮肤数等）
  ├─ 皮肤质量匹配（skin_quality.py，63 款高低分对照）
  ├─ 规则引擎评分（加权计算性价比 + 出租适配度）
  └─ LLM 复核（可选，注入用户自定义规则）
  │
  ▼
Replanner ── 判断信息是否充足，决定继续或结束
  │
  ▼
SSE 流式返回报告
```

---

## 皮肤质量评分体系

`app/tools/skin_quality.py` 维护了一份精选皮肤价值对照表，不仅按稀有度分类，更按**社区口碑**打分（-4 ~ +11）：

- **高分皮肤**：如安琪拉颠倒童话魔镜 (+10)、李信一念神魔 (+5) 等，命中后显著提升估值
- **弱款皮肤**：如鲁班七号星空梦想 (-4)、武则天神器明辉仪 (-3) 等，虽为稀有皮但口碑差，命中后压低估值

规则引擎和 LLM 复核均会引用该评分。用户也可在 Web 端 **规则配置** 面板中自定义皮肤质量规则，保存后自动替换默认策略。

---

## API 文档

### 评估

```http
POST /api/evaluate
Content-Type: application/json
```

请求体：

```json
{
  "session_id": "web-1715932800000",
  "url": "https://www.pxb7.com/buy/10013/1?keyword=王者荣耀",
  "detail_text": "售价1300，3典藏，3无双，2珍品传说，30传说，400皮肤",
  "purpose": "共号/出租变现",
  "min_price": 800,
  "max_price": 2000,
  "max_items": 60,
  "use_model": true,
  "custom_rules": {
    "skin_quality": "珍品传说：\nT0 天花板\n马可波罗 - 怪盗基德...",
    "system_prompt": "请用更严格的评分标准...",
    "baseline": "{\"price\": 1500, \"collections\": 4}"
  }
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `url` | string? | 螃蟹平台商品链接或列表页链接 |
| `detail_text` | string? | 商品详情文案（url 和 detail_text 至少提供一个） |
| `purpose` | string | 购买用途，默认"共号/出租变现" |
| `min_price` / `max_price` | number? | 预算区间 |
| `max_items` | int | 列表页最多抓取数量（1-200，默认 60） |
| `use_model` | bool | 是否使用 LLM 复核（默认 true） |
| `custom_rules` | object? | 用户自定义规则，见下方说明 |

返回 SSE 流，事件类型包括：

| event.type | 含义 |
|---|---|
| `plan` | Planner 制定完成，附带步骤列表 |
| `step_complete` | 单步执行完成 |
| `report_preview` | 规则评分先行报告（LLM 复核仍在运行） |
| `llm_batches_planned` | LLM 复核分批规划 |
| `llm_batch_start` | 开始某一批复核 |
| `llm_delta` | LLM 逐 token 增量输出 |
| `llm_batch_complete` | 某一批复核完成 |
| `report` | 最终报告 |
| `complete` | 评估全流程完成 |
| `error` | 出错 |

### 认证

```http
POST /api/auth/register
{"username": "user", "password": "1234"}

POST /api/auth/login
{"username": "user", "password": "1234"}

GET /api/auth/me
Authorization: Bearer <token>
```

### 规则管理（需认证）

```http
GET  /api/rules
Authorization: Bearer <token>

PUT  /api/rules/{rule_type}
Authorization: Bearer <token>
{"content": "自定义规则文本...", "title": "可选标题"}
```

`rule_type` 可选值：

| 类型 | 注入位置 |
|---|---|
| `skin_quality` | 替换 LLM 消息中的 `skin_quality_policy` 字段 |
| `system_prompt` | 追加到 LLM 系统提示词末尾 |
| `baseline` | 替换默认基准线（JSON 格式，如 `{"price": 1500, "collections": 4}`） |

### 健康检查

```http
GET /api/health
→ {"status": "ok"}
```

---

## 项目结构

```
app/
  core/
    database.py        # MySQL 连接、建库建表、迁移
    auth.py            # bcrypt 密码哈希、JWT 签发/验证
    deps.py            # FastAPI 依赖注入（JWT 用户提取）
    llm.py             # OpenAI 兼容 LLM 客户端（HTTP 流式）
  models/
    request.py         # EvaluateRequest
    account.py         # AccountMetrics, EvaluationResult
    user.py            # RegisterRequest, LoginRequest, TokenResponse
  agent/account/
    state.py           # AccountAgentState (TypedDict)
    planner.py         # Planner 节点 — 制定执行计划
    executor.py        # Executor 节点 — 逐步执行工具调用
    replanner.py       # Replanner 节点 — 判断继续或结束
  api/
    evaluate.py        # POST /api/evaluate（SSE 流式）
    auth.py            # POST /api/auth/register, /login, GET /me
    rules.py           # GET /api/rules, PUT /api/rules/{type}
  services/
    account_agent_service.py  # LangGraph 编排 + 事件队列
  tools/
    skin_quality.py    # 皮肤质量评分表 + 匹配引擎
    scorer.py          # 规则引擎评分
    extractor.py       # 正则字段提取 + 皮肤质量匹配
    model_reviewer.py  # LLM 评估（批量/单账号）
    reporter.py        # Markdown 报告生成
    pxb7_crawler.py    # 螃蟹列表页抓取调度
    fetcher.py         # 单商品链接文本读取
static/
  index.html           # 主页（评估表单 + 执行过程 + 报告）
  login.html           # 登录/注册页
  app.js               # 前端逻辑（SSE 解析、规则管理、认证）
  login.js             # 登录页逻辑
  styles.css           # 全局样式
scripts/
  pxb7_crawler.mjs     # Playwright + Chrome 列表页抓取脚本
tests/
  test_extract_and_score.py
  test_pxb7_batch_report.py
```

---

## 数据库

MySQL 数据库 `honor_evaluator` 在首次启动时自动创建。包含两张表：

**users**

| 列 | 类型 | 说明 |
|---|---|---|
| id | INT AUTO_INCREMENT PK | |
| username | VARCHAR(50) UNIQUE | 用户名 |
| password_hash | VARCHAR(255) | bcrypt 哈希 |
| created_at | TIMESTAMP | 注册时间 |

**user_rules**

| 列 | 类型 | 说明 |
|---|---|---|
| id | INT AUTO_INCREMENT PK | |
| user_id | INT FK → users.id | |
| rule_type | VARCHAR(50) | skin_quality / system_prompt / baseline |
| title | VARCHAR(200) | 可选标题 |
| content | MEDIUMTEXT | 规则文本（最大 16MB） |
| updated_at | TIMESTAMP | 最后修改时间 |

---

## 螃蟹列表页抓取

示例列表页链接：

```
https://www.pxb7.com/buy/10013/1?keyword=%E7%8E%8B%E8%80%85%E8%8D%A3%E8%80%80
```

抓取流程通过 `scripts/pxb7_crawler.mjs` 调用本机 Chrome（Playwright）自动滚动页面并监听懒加载 API。默认最多抓取 60 个商品，前端可调整到 1-200。

如果 Chrome 安装在非标准路径，设置环境变量：

```powershell
$env:CHROME_PATH="你的 chrome.exe 路径"
```

---

## 后续可扩展

- Playwright 浏览器自动化读取已登录页面
- 截图 OCR 提取商品字段
- 批量链接排名
- 平台成交价样本做动态估值
- 皮肤质量规则的结构化解析（目前为自然语言注入 LLM）
- 规则版本历史、恢复
