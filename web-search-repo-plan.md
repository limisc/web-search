# Web Search Repo Plan

> 目标：在你的 VPS 上部署一个**私有的、可远程访问的 web-search service**，先从 **Tavily** 开始，后续可扩展到 **Exa / Brave / Grok / Jina / 其他搜索与抽取服务**，并最终支持多 provider fan-out、交叉验证、去重、归一化与答案综合。

---

## 0. 结论先说

### 技术路线建议

**MVP 推荐：Python + FastMCP + httpx + Pydantic + uv**

理由：
- 这个项目本质上是**网络 I/O 密集型**，不是 CPU 密集型；Python 完全够用
- MCP 官方 Python SDK 是 Tier 1，生态成熟
- FastMCP 对“快速做出一个能跑的 MCP server”非常友好
- Tavily / Exa / Brave / Jina 这些 provider 本身就是 HTTP API，Python async 体验很好
- 在 VPS 上用 Docker / systemd / uvicorn 部署都很顺手

### 语言选择建议

- **现在就做 MVP：Python**
- **以后如果要追求极致轻量、静态二进制、极高并发：再考虑 Go 重写**

目前完全没必要一开始就用更“快”的语言。你的瓶颈主要会是：
- 外部 provider 延迟
- HTTP 超时 / 重试策略
- 结果归一化与综合逻辑
- 部署与认证

而不是 Python 本身。

---

## 1. 官方 MCP 文档提炼出来的关键设计约束

基于官方文档：
- https://modelcontextprotocol.io/docs/getting-started/intro
- https://modelcontextprotocol.io/docs/learn/architecture
- https://modelcontextprotocol.io/docs/learn/server-concepts
- https://modelcontextprotocol.io/docs/learn/client-concepts
- https://modelcontextprotocol.io/specification/2025-11-25
- https://modelcontextprotocol.io/docs/develop/build-server
- https://modelcontextprotocol.io/docs/develop/connect-remote-servers
- https://modelcontextprotocol.io/docs/sdk

### 1.1 MCP 的角色划分

MCP 里有三个角色：
- **Host**：Claude / ChatGPT / IDE / 你的 agent 宿主
- **Client**：Host 内部连某一个 MCP server 的连接器
- **Server**：提供工具、资源、提示词能力的服务

你的项目是：
- **一个 MCP server**
- 专门暴露“搜索与网页信息抽取”的能力

### 1.2 这个搜索服务最适合先做成 Tools，而不是 Resources / Prompts

官方定义里，Server 可以暴露：
- **Tools**：模型主动调用的动作
- **Resources**：被动读取的数据源
- **Prompts**：模板化工作流

对于搜索场景，MVP 最适合先做：
- `web_search`
- `web_extract`

也就是**先做 Tools**。

为什么：
- 搜索本身是动作，不是静态上下文
- 参数化程度高（query、domains、depth、时间范围等）
- 更符合 LLM 调用习惯

Resources 可以后面再做，比如：
- `search://cached/{query_hash}`
- `search://report/{job_id}`

Prompts 也可以后面再做，比如：
- `compare-sources`
- `fact-check-claim`

但都不是 MVP 必需。

### 1.3 两种标准传输：stdio 与 Streamable HTTP

官方当前重点是：
- **stdio**：本地开发、桌面客户端最稳
- **Streamable HTTP**：远程部署到 VPS 的推荐方式

建议：
- **本地开发 / Inspector 调试：stdio**
- **VPS 远程部署：Streamable HTTP**

### 1.4 Server 应该“聚焦、可组合、边界清晰”

官方架构强调：
- server 应该职责单一
- 多 server 可以组合
- host 负责上下文聚合
- server 不应该变成“万能代理层”

所以这个 repo 不要变成：
- 任意 URL 抓取代理
- 通用 HTTP 代理
- 任意 shell 执行服务

而应该保持为：
- 搜索 provider 封装
- 结果归一化
- citation 输出
- 统一 tool schema
- 后续 provider 共识 / 交叉验证

### 1.5 远程 HTTP 要认真考虑认证与安全

官方规范强调：
- HTTP transport 下认证是可选的，但如果做，要尽量贴近规范
- 对自用场景，也必须有清晰的安全边界
- 不要把一个有搜索与外部访问能力的 MCP endpoint 裸暴露到公网

MVP 安全建议：
- 优先：`127.0.0.1` + SSH Tunnel / Tailscale
- 如果必须公网 HTTPS：
  - 走 Caddy / Nginx 反代
  - TLS
  - Bearer Token / 反向代理鉴权
  - IP allowlist / 基础 rate limit

OAuth / 标准 MCP auth 可以放到后续版本。

---

## 2. 社区方案与实现趋势总结

基于社区资料与检索到的内容：
- PrefectHQ/fastmcp
- modelcontextprotocol/python-sdk
- gofastmcp.com 文档
- Azure remote MCP auth sample
- AWS MCP deployment guidance
- awesome-mcp-servers
- 一些社区 issue / 经验贴

### 2.1 现实中 Python FastMCP 路线非常主流

社区主流做法：
- 用 Python 写业务逻辑
- 用 FastMCP 或官方 Python SDK 暴露为 MCP
- 本地走 stdio
- 远程走 HTTP/streamable-http

这条路对于你的 MVP 是最省时间的。

### 2.2 远程 HTTP 真正常见的问题不是“协议”，而是“部署细节”

社区里最常见的坑：
- endpoint 路径不对（如 `/mcp`）
- 反代把流式响应 / 长连接搞坏
- 认证头没透传
- CORS / Origin / 代理层配置不正确
- 局域网能 ping 通，但 client 仍然 `fetch failed`
- tool 超时太短
- provider 很慢，client 误以为 server 坏了

所以 MVP 一开始就要有：
- `/healthz`
- request id / latency 日志
- 明确的 timeout 配置
- 结构化错误返回
- 本地 Inspector 验证链路

### 2.3 生产上大家会把 MCP server 当成“标准 Web 服务”来运维

也就是：
- Docker 镜像
- uvicorn / ASGI
- 反向代理
- 环境变量注入 API key
- 健康检查
- 基础日志 / 指标

这正适合放 VPS。

### 2.4 真正难的是“结果模型设计”，不是 Tavily 接进来

接 Tavily API 并不难。
真正会决定后面扩展速度的是：
- 统一输入 schema
- 统一输出 schema
- provider adapter 接口
- citation 结构
- 去重 / 归一化逻辑

所以 MVP 虽然只做 Tavily，也应该**先把抽象层做好**。

---

## 3. MVP 目标与非目标

## 3.1 MVP 目标

V0.1 只做下面这些：

### 必做
- 一个可运行的 Web Search MCP server
- 支持 **Tavily Search**
- 支持 **Tavily Extract**
- 暴露统一工具：
  - `web_search`
  - `web_extract`
- 本地支持 `stdio`
- VPS 支持 `Streamable HTTP`
- 返回标准化 citations
- 具备基本超时、重试、错误处理
- Docker 化

### 强烈建议一起做
- `/healthz`
- 结构化日志
- 请求耗时统计
- provider 返回的原始响应保留到 debug 字段（默认不返回给模型）
- 简单缓存（可选：内存 / SQLite）

## 3.2 明确不做

这些放到 V0.2 / V0.3：
- Exa / Brave / Grok / Jina 多 provider 真正 fan-out
- 多 provider 共识裁决
- 深度 research workflow
- crawl 工具
- OAuth / 动态客户端注册
- prompt / resource 体系
- 管理后台
- 多租户
- 用户配额系统

---

## 4. MVP 的工具设计

建议不要一开始暴露很多 provider-specific tools。

### MVP 工具建议

#### 4.1 `web_search`
统一搜索入口。

**输入建议：**

```json
{
  "query": "string",
  "provider": "tavily",
  "max_results": 5,
  "topic": "general",
  "time_range": "day",
  "include_domains": ["example.com"],
  "exclude_domains": ["reddit.com"],
  "search_depth": "basic",
  "include_answer": true,
  "include_raw_content": false
}
```

**字段说明：**
- `query`: 搜索词
- `provider`: MVP 固定只接受 `tavily`
- `max_results`: 1-10 或 1-20
- `topic`: `general | news`
- `time_range`: `day | week | month | year`，可选
- `include_domains`: 白名单域名
- `exclude_domains`: 黑名单域名
- `search_depth`: `basic | advanced`
- `include_answer`: 是否让 provider 返回摘要答案
- `include_raw_content`: 是否附带较长页面正文

**输出建议：**

```json
{
  "query": "...",
  "provider": "tavily",
  "answer": "...",
  "results": [
    {
      "title": "...",
      "url": "https://...",
      "snippet": "...",
      "content": "...",
      "score": 0.92,
      "published_at": null,
      "source_type": "web",
      "provider": "tavily"
    }
  ],
  "citations": [
    {
      "title": "...",
      "url": "https://..."
    }
  ],
  "meta": {
    "latency_ms": 1240,
    "cached": false,
    "provider_request_id": null
  }
}
```

#### 4.2 `web_extract`
已知 URL 的内容抽取。

**输入建议：**

```json
{
  "urls": ["https://example.com/a"],
  "provider": "tavily",
  "extract_depth": "basic",
  "query": "authentication",
  "max_chunks": 3,
  "format": "markdown"
}
```

**输出建议：**

```json
{
  "provider": "tavily",
  "pages": [
    {
      "url": "https://example.com/a",
      "title": "...",
      "content": "...",
      "excerpt": "...",
      "chunks": ["..."],
      "provider": "tavily"
    }
  ],
  "meta": {
    "latency_ms": 860,
    "cached": false
  }
}
```

---

## 5. 为什么 MVP 不建议一开始就做 `web_verify`

虽然 `web_verify` 很诱人，但如果只有 Tavily，一个所谓“验证”其实仍然只是在单 provider 里做检索与再总结。

那样很容易让接口语义变假：
- 名字叫 verify
- 实际只是 second-pass search

所以更建议：
- V0.1：`web_search` + `web_extract`
- V0.2：引入第二个 provider 后，再做 `web_verify` / `web_compare`

届时验证才真的成立：
- provider A 搜索
- provider B 再查
- 做交叉比对 / 一致性判断 / 冲突提示

---

## 6. 推荐架构

```text
MCP Host / Client
      |
      v
+----------------------+
|   web-search service  |
|  (FastMCP / Python)  |
+----------------------+
      |
      +--> tools/web_search
      |       |
      |       v
      |   services/search_service.py
      |       |
      |       v
      |   providers/tavily.py
      |       |
      |       v
      |   normalize/search_result.py
      |
      +--> tools/web_extract
              |
              v
          services/extract_service.py
              |
              v
          providers/tavily.py
```

### 6.1 分层建议

#### MCP layer
负责：
- tool 注册
- 输入 schema
- 输出包装
- MCP transport
- 错误映射

#### Service layer
负责：
- 参数校验
- timeout / retry / cache
- provider 选择
- 聚合 / 归一化

#### Provider adapter layer
负责：
- 调 Tavily API
- 映射 Tavily 特有字段
- 屏蔽 provider 差异

#### Normalize layer
负责：
- 统一 SearchHit / Citation / ExtractPage 数据结构
- 为未来 Exa / Brave / Grok 做兼容

---

## 7. 推荐的数据模型

建议从一开始就定义统一模型。

### 7.1 核心模型

#### `SearchRequest`
- query
- provider
- max_results
- topic
- time_range
- include_domains
- exclude_domains
- search_depth
- include_answer
- include_raw_content

#### `SearchHit`
- title
- url
- snippet
- content
- score
- published_at
- source_type
- provider
- raw

#### `Citation`
- title
- url
- provider

#### `SearchResponse`
- query
- provider
- answer
- results
- citations
- meta

#### `ExtractRequest`
- urls
- provider
- extract_depth
- query
- max_chunks
- format

#### `ExtractedPage`
- url
- title
- content
- excerpt
- chunks
- provider
- raw

### 7.2 为什么一定要有 `raw`

因为未来接 Exa / Brave / Grok 时：
- 每家返回字段不一样
- 你会经常需要 debug provider 差异

所以建议：
- 归一化字段给上层与模型使用
- 原始 provider 响应保留在 `raw`
- 默认不给模型，只在 debug 模式 / 日志里可见

---

## 8. 推荐仓库结构

```text
web-search/
  README.md
  pyproject.toml
  uv.lock
  .env.example
  Dockerfile
  docker-compose.yml
  src/
    web_search/
      __init__.py
      app.py
      config.py
      logging.py
      tools/
        web_search.py
        web_extract.py
      services/
        search_service.py
        extract_service.py
      providers/
        base.py
        tavily.py
      models/
        requests.py
        responses.py
        provider.py
      normalize/
        search.py
        extract.py
      utils/
        http.py
        errors.py
        cache.py
        timeouts.py
  tests/
    test_tavily_adapter.py
    test_web_search_tool.py
    test_web_extract_tool.py
    test_normalization.py
  docs/
    architecture.md
    deployment.md
    tools.md
    roadmap.md
```

---

## 9. 推荐技术栈

### 核心
- **Python 3.11+**
- **fastmcp**（或官方 Python SDK 的 FastMCP 路线）
- **httpx**（async）
- **pydantic**
- **uv**（依赖与运行）

### 辅助
- `pytest`
- `pytest-asyncio`
- `respx` 或 `httpx.MockTransport`（provider API mock）
- 可选 `tenacity`（重试）

### 日志
- 标准 logging 即可，后面再结构化
- stdio 模式下务必**不要往 stdout 打非 MCP 内容**
- 所有日志走 stderr / 文件

---

## 10. FastMCP vs 官方 Python SDK：怎么选

### 推荐方案
**优先用 FastMCP 快速起盘，但业务层保持框架无关。**

也就是：
- `tools/*.py` 里和 FastMCP 绑定
- `services/` `providers/` `models/` 全部不依赖 MCP 框架

这样以后：
- 要切换到官方更底层 SDK
- 要把能力包装成 HTTP API / CLI
- 要复用到别的 Agent 框架

都很容易。

### 选择依据

#### FastMCP 优点
- 开发速度快
- API 直观
- HTTP 部署文档成熟
- 适合 MVP

#### 官方 SDK 优点
- 更贴近规范
- 示例齐全
- 长期稳定性强

### 最务实建议
- **MVP：FastMCP**
- **抽象层要干净**

---

## 11. Tavily Provider 设计

### 11.1 Tavily 在 MVP 里负责什么

只接两个能力：
- Search
- Extract

先不接：
- crawl
- research

原因：
- search + extract 已经足够形成实用 MVP
- crawl / research 更贵、更慢、更容易把上下文打爆
- 真正需要多 provider 协调前，没必要过早加复杂模式

### 11.2 Tavily adapter 建议接口

```python
class SearchProvider(Protocol):
    async def search(self, request: SearchRequest) -> SearchResponse: ...
    async def extract(self, request: ExtractRequest) -> ExtractResponse: ...
```

```python
class TavilyProvider(SearchProvider):
    async def search(self, request: SearchRequest) -> SearchResponse: ...
    async def extract(self, request: ExtractRequest) -> ExtractResponse: ...
```

### 11.3 Tavily 配置建议

环境变量：
- `TAVILY_API_KEY` 必填
- `TAVILY_BASE_URL` 可选
- `REQUEST_TIMEOUT_SECONDS` 默认 20~30
- `RETRY_MAX_ATTEMPTS` 默认 2 或 3

---

## 12. MVP 运行模式设计

## 12.1 本地开发

### 模式 A：stdio
用于：
- MCP Inspector
- 本地 client 调试
- schema 验证

### 模式 B：本地 HTTP
用于：
- 提前验证远程 transport 行为
- 验证 `/mcp` 路径
- 测试反向代理配置

## 12.2 VPS 生产

推荐拓扑：

```text
Client
  |
HTTPS
  |
Caddy / Nginx
  |
127.0.0.1:8000
  |
FastMCP / Uvicorn app
```

### 推荐配置
- MCP endpoint: `/mcp`
- Health check: `/healthz`
- App 仅监听 `127.0.0.1`
- 反代做 TLS
- 反代做基础鉴权 / token 透传
- 反代设置较长 read timeout

---

## 13. 安全边界建议

### MVP 推荐边界

#### 最安全自用方案
- 服务仅监听 `127.0.0.1`
- 通过 SSH tunnel / Tailscale 访问
- `TAVILY_API_KEY` 只放服务端
- 不提供任意 URL fetch
- 不做通用浏览器代理

#### 如需公网可达
- HTTPS 必须有
- 反代加 bearer auth 或至少 secret header
- 加基本 rate limit
- 记录 request id
- 后续再考虑 MCP 规范化 OAuth

### 明确不建议
- 直接把未鉴权 MCP endpoint 裸露公网
- 任意 headers / method 转发
- 任意 URL fetch
- 同一个服务里塞太多无关能力

---

## 14. 超时、重试、错误处理建议

这是搜索 MCP 真正的生命线。

### 14.1 默认 timeout 建议
- provider request timeout: `20s`
- 总 tool timeout: `25s` 或 `30s`

### 14.2 重试建议
只对这些错误重试：
- connect timeout
- read timeout
- 502/503/504
- 明显瞬时网络错误

不要对这些重试：
- 401/403
- 参数错误
- provider schema 错误

### 14.3 错误返回建议
不要只返回 “search failed”。

要返回：
- provider
- error category
- user-friendly message
- debug meta（可选）

例如：

```json
{
  "error": {
    "type": "provider_timeout",
    "message": "Tavily request timed out after 20s",
    "provider": "tavily"
  }
}
```

---

## 15. 缓存建议

MVP 可以非常轻量。

### 可选方案 A：先不做缓存
适合：
- 先把协议跑通
- 先验证 tool 设计

### 可选方案 B：做一个很简单的 query 级缓存
推荐：
- key = 请求参数 hash
- TTL = 5~30 分钟
- 存内存或 SQLite

为什么值得做：
- 降低 Tavily 调用成本
- 重复问题秒回
- 对 agent 非常友好

### 我建议
- **MVP 可以先留接口，第二个 commit 加缓存**

---

## 16. 测试策略

### 16.1 单元测试
- Tavily adapter 响应映射
- normalize 逻辑
- schema 校验

### 16.2 集成测试
- mock Tavily HTTP 响应
- 调用 `web_search`
- 调用 `web_extract`

### 16.3 手工 smoke test
- 本地用 Inspector 连 stdio
- 本地用 Inspector 连 HTTP `/mcp`
- 在 VPS 上通过反代地址连一次
- 跑几个固定 query：
  - `What is MCP?`
  - `latest OpenAI pricing`（news/general 区分）
  - 指定 domain 搜索

---

## 17. 部署建议

## 17.1 Docker 优先

优点：
- 干净
- 好迁移
- 好回滚
- VPS 上不污染 Python 环境

### 运行方式建议
- 单容器即可
- 反代独立
- `docker compose` 管理

## 17.2 Dockerfile 重点
- 基于 slim Python 镜像
- 安装依赖
- 使用非 root 用户
- 环境变量注入 API keys
- 暴露 8000

## 17.3 健康检查
至少要有：
- `/healthz` 返回 200

可选：
- `provider_status` 内部检查 Tavily key 是否存在

---

## 18. Roadmap

## Phase 1：本地可运行 MVP
- 初始化 repo
- 接入 FastMCP
- 实现 `web_search`
- 实现 `web_extract`
- 本地 stdio 调试
- 单元测试

## Phase 2：远程部署
- HTTP transport
- `/mcp` endpoint
- `/healthz`
- Docker 化
- VPS 部署
- 反代 + TLS

## Phase 3：体验优化
- 缓存
- 结构化日志
- request id / latency
- 更好的错误模型

## Phase 4：多 provider 扩展
- `providers/exa.py`
- `providers/brave.py`
- `providers/jina.py`
- `providers/grok.py`
- 统一 fan-out / rank / dedupe / consensus

## Phase 5：验证与综合
- `web_verify`
- `web_compare`
- 多源一致性评分
- 结果冲突提示

---

## 19. V0.2 / V0.3 提前预留的抽象

虽然 MVP 只支持 Tavily，但代码里建议预留下面这些概念：

### 19.1 Orchestrator
未来统一入口：
- single provider
- fan-out multi provider
- fallback provider
- compare / verify

### 19.2 Ranking / Dedup
未来要做：
- URL 规范化
- 同站点相似内容折叠
- 标题去重
- provider 间重复结果合并

### 19.3 Consensus
未来可能输出：
- `agreement_score`
- `conflicts`
- `provider_coverage`
- `confidence`

这些都先不要实现，但模型要想清楚。

---

## 20. 一个务实的 MVP 版本定义

### V0.1
- `web_search`
- `web_extract`
- Tavily only
- stdio + HTTP
- Docker
- VPS 可跑

### V0.2
- Exa adapter
- `web_verify`
- 统一 citation / dedupe
- timeout / retry / cache 完善

### V0.3
- Brave / Jina / Grok
- provider fan-out
- consensus
- provider routing 策略

---

## 21. 推荐的第一批实现文件

最小可交付可以只写这些：

```text
src/web_search/app.py
src/web_search/config.py
src/web_search/tools/web_search.py
src/web_search/tools/web_extract.py
src/web_search/providers/base.py
src/web_search/providers/tavily.py
src/web_search/models/requests.py
src/web_search/models/responses.py
tests/test_tavily_adapter.py
README.md
Dockerfile
.env.example
```

---

## 22. 我对这个项目的最终建议

### 方案定稿建议

- **新开 repo**：`web-search`
- **语言**：Python
- **框架**：FastMCP
- **provider**：先只做 Tavily
- **工具**：先只做 `web_search` + `web_extract`
- **传输**：本地 stdio，VPS 用 Streamable HTTP
- **部署**：Docker + Caddy/Nginx
- **安全**：先自用边界，不要裸公网

### 最重要的取舍
不要一开始就把这些全塞进去：
- Exa
- Brave
- Grok
- Jina
- crawl
- research
- consensus
- OAuth

那样你会把大量时间花在：
- 兼容差异
- provider 不稳定
- schema 演化
- transport / auth / 部署联调

而不是先把真正可用的搜索 MCP 跑起来。

---

## 23. 参考资料

### 官方 MCP
- Intro: https://modelcontextprotocol.io/docs/getting-started/intro
- Architecture: https://modelcontextprotocol.io/docs/learn/architecture
- Server Concepts: https://modelcontextprotocol.io/docs/learn/server-concepts
- Client Concepts: https://modelcontextprotocol.io/docs/learn/client-concepts
- Specification 2025-11-25: https://modelcontextprotocol.io/specification/2025-11-25
- Build a Server: https://modelcontextprotocol.io/docs/develop/build-server
- Connect Remote Servers: https://modelcontextprotocol.io/docs/develop/connect-remote-servers
- SDKs: https://modelcontextprotocol.io/docs/sdk
- Transports: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- Authorization: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization

### Python / FastMCP / 社区实践
- MCP Python SDK: https://github.com/modelcontextprotocol/python-sdk
- FastMCP Repo: https://github.com/PrefectHQ/fastmcp
- FastMCP Tutorial: https://gofastmcp.com/tutorials/create-mcp-server
- FastMCP HTTP Deployment: https://gofastmcp.com/deployment/http
- FastMCP Running Your Server: https://gofastmcp.com/deployment/running-server
- Azure remote MCP auth sample: https://github.com/Azure-Samples/remote-mcp-webapp-python-auth
- AWS deployment guidance: https://github.com/aws-solutions-library-samples/guidance-for-deploying-model-context-protocol-servers-on-aws
- Awesome MCP servers: https://github.com/punkpeye/awesome-mcp-servers

### Tavily
- 通过当前 skill 脚本与官方 API 路线可先落地 Search / Extract，两者已经足够支持 MVP。

---

## 24. 下一步建议

现在最适合立刻做的是：

1. 初始化 Python repo
2. 加 FastMCP 与依赖
3. 定义统一 Pydantic models
4. 写 Tavily adapter
5. 暴露 `web_search`
6. 暴露 `web_extract`
7. 本地 Inspector 测通
8. Docker 化
9. 部署到 VPS

如果继续推进，下一步我可以直接帮你：

### 选项 A：直接生成 repo 骨架
我会在当前目录下生成：
- `pyproject.toml`
- `src/web_search/...`
- `Dockerfile`
- `.env.example`
- 最小可运行 Tavily Web Search MCP server

### 选项 B：先把协议 / schema 定死
我先给你写：
- `web_search` 输入输出 schema
- `web_extract` 输入输出 schema
- provider adapter interface

### 选项 C：先写部署版架构
我先给你：
- Docker Compose
- Caddy / Nginx 反代示例
- VPS 部署说明

---

## 一句话总结

**这个项目最合理的起点是：Python + FastMCP，先做 Tavily 的 `web_search` / `web_extract`，本地 stdio 调试，VPS 上用 Streamable HTTP 部署；把 provider 抽象与归一化先设计好，再逐步扩展 Exa / Brave / Grok / Jina。**
