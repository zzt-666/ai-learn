# Proposal

## Why

当前出题只能依赖模型知识或公开网页检索，无法覆盖企业内部培训、客服知识库、专项题库、内部文档等私有资料。用户需要把 pdf / docx / markdown 建成可隔离的知识库，再按「材料优先」闯关学习；同时首页文本开局应能在「私有库检索」与「联网搜索」之间由 Agent 智能路由。

## What Changes

- 用户可创建多个**命名知识库**（领域隔离），向指定库上传 **pdf / docx / markdown**，服务端解析、切分、用百炼 `text-embedding-v4` 向量化后写入 **Chroma**。
- 「题目」Tab 从占位改为真实**知识库管理**：建库、列表、上传、文档状态、删除；可从某一知识库发起闯关（**强制走知识库检索**，材料优先，不走 Tavily）。
- 首页文本开局改为 **Agentic RAG 路由**：
  - 用户**没有任何已就绪知识库/文档**时：仅联网搜索（与现行为接近，失败仍静默降级模型知识）。
  - 用户**有就绪知识库**时：Agent 自主选择调用知识库检索工具和/或联网搜索工具取知后再出题。
- 出题 Prompt / 模式分流：知识库路径「材料优先、少编造库外事实」；纯联网/模型路径保持现有探索口径。
- 出题请求契约**向后兼容**地增加可选 `knowledge_base_id`（及必要的任务字段）；未传时走首页 Agent 路由。
- **不做**：知识库分享/协作、网页/视频入库、未完成局云续玩、错题重练、固定题包导入（只存题不走 RAG）、企业班级管理。

## Capabilities

### New Capabilities

- `knowledge-base`: 多知识库 CRUD、文档上传与入库管线（解析/切分/Embedding/Chroma）、文档与库生命周期、权限隔离与题库 Tab 管理体验。

### Modified Capabilities

- `quiz-generation`: 首页由「每次必尝试联网」改为 Agentic 路由（无库→仅联网；有库→库内检索与/或联网）；新增强制知识库开局模式与材料优先出题规则；可选 `knowledge_base_id` 扩展请求契约。

## Impact

- **后端**：新增知识库/文档表与 Alembic 迁移；上传目录与 Chroma persist；入库与检索服务；扩展现有 `create_agent` 研究链路与 quiz 异步任务；`DASHSCOPE_API_KEY` 等环境变量；依赖 `langchain-chroma`、`chromadb`、`dashscope`/`openai`（兼容 Embedding）、PDF/DOCX 解析库。
- **API**：知识库与文档 REST；出题/异步任务增加可选 `knowledge_base_id`；登录与越权校验沿用现有 JWT。
- **前端（Taro 4）**：重做 `pages/bank`；上传用 `chooseMessageFile` + `uploadFile`；从库开局复用现有 generate/quiz/report 流程。
- **不动**：通关结算公式、历史重闯打乱策略、分享/游客。
- **外部**：百炼 Embedding 额度与密钥；Chroma 本地磁盘；DeepSeek tool calling。
