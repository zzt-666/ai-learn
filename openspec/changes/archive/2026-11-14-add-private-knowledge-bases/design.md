# Design

## Context

- 产品已有：静默登录 + MySQL 用户/通关局；异步出题任务（`quiz_generation_tasks`）；首页出题经 `create_agent` + Tavily 工具取知，再 `with_structured_output` 生成题目（见 `quiz_research.py` / `quiz_service.py`）。
- 「题目」Tab（`pages/bank`）仍为占位。
- 动机与范围见 `proposal.md`；行为契约见 `specs/knowledge-base`、`specs/quiz-generation`。
- 已确认：多命名知识库隔离；首页 Agentic 路由（无就绪库→仅联网；有库→库检索与/或联网）；从库开局强制 RAG；Embedding = 百炼 `text-embedding-v4`；向量库 = Chroma。

## Goals / Non-Goals

**Goals:**

- 一人可维护：MySQL 管元数据，本机 Chroma persist 管向量；入库异步；出题复用现有异步任务与闯关页。
- 领域隔离：按「知识库」限定检索范围，避免跨库串题。
- 首页与题库两条入口共用同一套检索/出题内核，仅工具集与 Prompt 模式不同。

**Non-Goals:**

- 分布式向量集群、跨用户共享库、在线编辑文档正文、OCR 扫描件、网页/视频入库。
- 改 EXP/历史/重闯公式；展示检索来源 UI。

## Decisions

### 1. 数据模型（MySQL 元数据 + Chroma 向量）

| 表 | 要点 |
|----|------|
| `knowledge_bases` | `id`, `user_id`, `name`, `description?`, `created_at`, `updated_at`；索引 `(user_id, updated_at)` |
| `knowledge_documents` | `id`, `knowledge_base_id`, `user_id`, `filename`, `content_type`, `size_bytes`, `storage_path`, `status`(`pending`/`processing`/`ready`/`failed`), `error_message`, `chunk_count`, `created_at`, `updated_at` |

- 删除库：级联删文档行 + 删磁盘文件 + 删 Chroma 中该库全部 chunk ids。
- `quiz_generation_tasks` 增加可空 `knowledge_base_id`（强制库模式）；`source_text` 在库开局可用主题名/用户补充说明，允许短文本（仍 trim 非空；库开局可由前端填默认线索如「根据本知识库出题」）。

**备选**：向量也存 MySQL → 否（无现成 ANN，偏离选型）。  
**备选**：单总库 + 文档勾选 → 否（已确认多库）。

### 2. Chroma 组织方式

- 单一 `persist_directory`（如 `chroma_data/`，gitignore）。
- **每个知识库一个 collection**：名 `kb_{knowledge_base_id}`（稳定、短）。
- Chunk metadata：`user_id`, `knowledge_base_id`, `document_id`, `filename`, `chunk_index`。
- 检索强制 `filter`：`knowledge_base_id`（强制模式固定一库；首页 Agent 工具按库 id 检索，禁止跨用户）。
- 使用官方集成：`langchain-chroma` 的 `Chroma(collection_name=..., embedding_function=..., persist_directory=...)`；`add_documents` / `similarity_search(..., k=..., filter=...)`（Context7 / LangChain docs）。

**备选**：全用户一个 collection 仅靠 metadata → 隔离弱、误滤风险高，不采用。

### 3. Embedding：百炼 `text-embedding-v4`

- 环境变量：`DASHSCOPE_API_KEY`（必填才能入库/检索）；可选 `DASHSCOPE_EMBEDDING_MODEL=text-embedding-v4`、`DASHSCOPE_EMBEDDING_DIMENSIONS=1024`（官方默认 1024，兼顾效果与存储）。
- 调用优先 **OpenAI 兼容模式**（便于与 LangChain `OpenAIEmbeddings` 或薄封装对接），`base_url` 按百炼文档配置；实现时以 [百炼 Embedding 文档](https://help.aliyun.com/zh/model-studio/embedding) 为准再核对。
- 入库文本 `text_type=document`；查询侧若 API 支持则用 `query`（兼容层若无该参数则统一 dense 1024）。
- 单批 ≤ 10 条、单条 ≤ 8192 token：切分后批量 embed，超长 chunk 再切。

**备选**：DeepSeek embedding → 用户已指定百炼，不采用。

### 4. 文档解析与切分

| 类型 | 解析 |
|------|------|
| pdf | `pypdf` 或 `pymupdf`（优先抽文本；扫描件无字则标记失败「无法提取文本」） |
| docx | `python-docx` |
| md | UTF-8 读文本（尝试 utf-8-sig / gbk 回退） |

- 切分：`RecursiveCharacterTextSplitter`（chunk ~800–1000 字，overlap ~100–150）；中文按字符计。
- 上传落盘：`uploads/knowledge/{user_id}/{kb_id}/{doc_id}_{safe_name}`。
- 入库流水线：上传 → 行 `pending` → BackgroundTasks（或同 quiz 任务模式）→ `processing` → parse/split/embed/add → `ready`；异常 → `failed` + `error_message`。
- 限额（可配置）：单文件 10MB；单库文档 ≤ 20；每用户库 ≤ 10。

### 5. 出题取知：扩展现有 Agent，而非并行两套引擎

复用 `gather_research_context` 模式（`langchain.agents.create_agent` + tools → 文本上下文 → structured quiz）：

```text
首页未传 knowledge_base_id:
  if user 无就绪库 → tools = Tavily*（现状）
  else → tools = Tavily* + kb_list_ready + kb_retrieve(kb_id, query)
  失败 → 静默模型知识

传 knowledge_base_id（题库开局）:
  校验归属 + 至少 1 份 ready
  tools = 仅 kb_retrieve(该 kb_id, query)（可多 query）
  无可用片段 → 明确失败，禁止降级联网/模型冒充材料闯关
  有片段 → grounded Prompt「材料优先」
```

- `kb_retrieve`：在指定 collection 上 `similarity_search`，返回拼接片段（截断总长，与现 `_MAX_CONTEXT_CHARS` 同量级）。
- Prompt：新增 `QUIZ_SYSTEM_KB` / grounded-KB 变体；首页 Agent 选用库片段时同样走材料优先规则。
- 异步任务：`QuizTaskCreateRequest` 增加可选 `knowledge_base_id`；`generate_quiz(..., knowledge_base_id=, user_id=)` 贯穿 task runner。

### 6. API 草图

| 方法 | 路径 | 作用 |
|------|------|------|
| GET/POST | `/api/v1/knowledge-bases` | 列表 / 创建 |
| PATCH/DELETE | `/api/v1/knowledge-bases/{id}` | 改名 / 删库 |
| GET | `/api/v1/knowledge-bases/{id}/documents` | 文档列表 |
| POST | `/api/v1/knowledge-bases/{id}/documents` | multipart 上传 |
| GET | `/api/v1/knowledge-bases/{id}/documents/{doc_id}` | 状态 |
| DELETE | `/api/v1/knowledge-bases/{id}/documents/{doc_id}` | 删文档+向量 |
| POST | `/api/v1/quiz/tasks` | body 增加可选 `knowledge_base_id` |

错误码延续：`UNAUTHORIZED`、`NOT_FOUND`、`VALIDATION_ERROR`、`GENERATE_FAILED`；新增可读如 `KB_EMPTY`、`INGEST_FAILED`、`FILE_TOO_LARGE`、`UNSUPPORTED_FILE_TYPE`。

### 7. 前端（Taro 4.1.x）

- 重做 `pages/bank`：库列表、空态、创建；`pages/bank/detail`（新建）：文档列表、状态轮询、上传、删除、**开始闯关**。
- 选文件：`Taro.chooseMessageFile({ type: 'file', extension: ['pdf','docx','md','markdown'] })`——**extension 不要带点**（微信 iOS 兼容）。再 `Taro.uploadFile` + `Authorization: Bearer`，`name: 'file'`，`formData` 可空。
- 从库开局：写入本地 session 线索 → 调 `POST /quiz/tasks` 带 `knowledge_base_id` + 默认/可编辑主题名 → 复用现有 generate 轮询与 quiz/report。
- 首页：请求体仍可不传 `knowledge_base_id`；loading 文案可改为「正在智能取知出题…」类中性表述。

### 8. 依赖与配置增量

```text
# backend
langchain-chroma
chromadb
dashscope   # 或 openai 客户端走兼容 endpoint
pypdf       # 或 pymupdf
python-docx
# text splitter：langchain-text-splitters（若未随 langchain 带上）

DASHSCOPE_API_KEY=
DASHSCOPE_EMBEDDING_DIMENSIONS=1024
CHROMA_PERSIST_DIR=chroma_data
KB_MAX_FILE_BYTES=10485760
KB_MAX_DOCS_PER_BASE=20
KB_MAX_BASES_PER_USER=10
```

### 9. 测试策略（TDD 延续）

- 纯函数：切分、归属校验、限额、工具选择（有/无就绪库 / 强制库）。
- API：CRUD 越权 404；上传类型/大小；入库状态机（可用假 embedding）；强制库空库失败；首页无库仍可 mock 降级。
- Chroma：用临时 `persist_directory` 的集成测（可 mark integration）。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 微信小程序只能从「聊天文件」选文件，体验受限 | 文案说明；后续可再评 `chooseFile` 等能力，本期不阻塞 |
| PDF 扫描件无文本 | 失败态明确提示，不做 OCR |
| Chroma 本机文件锁 / 多进程 | 单 FastAPI worker 开发默认；文档注明勿多 worker 共写同一 persist（上线再评） |
| Embedding / 入库耗时与费用 | 异步状态 + 限额 + 1024 维；密钥缺失时上传可接受但 ingest 失败可读 |
| Agent 首页误用错库 | 工具描述强调「仅当主题与库名/领域相关时检索」；强制模式从 UI 选库无歧义 |
| 删除库后任务仍引用 | 出题前再校验库存在且有 ready 文档 |

## Migration Plan

1. Alembic：`knowledge_bases`、`knowledge_documents`；`quiz_generation_tasks.knowledge_base_id` 可空 FK。
2. 创建 `chroma_data/`、`uploads/knowledge/` 并 gitignore。
3. `.env.example` 增加百炼与 Chroma 项；本地填 `DASHSCOPE_API_KEY` 后再测入库。
4. 前端发版后旧客户端不传 `knowledge_base_id` 仍可用（首页路由逻辑服务端兼容）。
5. 回滚：关掉 KB 路由注册 + 前端入口；Chroma 目录可保留或删；迁移 down 需先清业务数据。

## Open Questions

- 无（影响规格与任务拆分的决策已在人工确认中锁定）。实现阶段若百炼兼容 endpoint 地域/Workspace 写法有变，以官方文档当场核对，不改行为规格。
