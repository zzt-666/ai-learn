# Tasks

## 1. 依赖与配置脚手架

- [x] 1.1 在 `backend/requirements.txt` 增加 `langchain-chroma`、`chromadb`、Embedding 客户端（`dashscope` 或 `openai` 兼容）、`pypdf`、`python-docx`、`langchain-text-splitters`（若需要），安装后 `pip show` 能看到对应包
- [x] 1.2 扩展 `Settings` / `.env.example`：`DASHSCOPE_API_KEY`、`DASHSCOPE_EMBEDDING_DIMENSIONS`、`CHROMA_PERSIST_DIR`、KB 限额项；启动时能读到默认值；`chroma_data/` 与 `uploads/knowledge/` 加入 gitignore 并本地可创建
- [x] 1.3 实现百炼 `text-embedding-v4` 薄封装（固定 1024 维），用 mock/假密钥单测覆盖「空输入拒绝 / 批量切分调用次数」；对照官方文档确认 base_url 与参数名

## 2. 数据模型与迁移

- [x] 2.1 新增 SQLAlchemy 模型 `KnowledgeBase`、`KnowledgeDocument` 与 Alembic 迁移；对测试库跑升级后表结构存在且 FK/索引符合 design
- [x] 2.2 为 `quiz_generation_tasks` 增加可空 `knowledge_base_id` 迁移；迁移后旧任务行可为 NULL，pytest DB fixture 仍可用
- [x] 2.3 编写知识库归属与限额纯函数测试（每用户库数、单库文档数、文件大小/后缀），测试先红后绿

## 3. 知识库 CRUD API

- [x] 3.1 实现 `GET/POST /api/v1/knowledge-bases` 与 `PATCH/DELETE /{id}`（需登录、仅本人）；pytest 覆盖创建/列表/改名/删除/越权 404
- [x] 3.2 删除知识库时级联删除文档元数据、磁盘文件与 Chroma collection（可用临时 persist 目录测）；验证删后 GET 404 且 collection 不存在或为空

## 4. 文档上传与异步入库

- [x] 4.1 实现 `POST .../documents` multipart 上传：校验类型（pdf/docx/md）、大小、配额；落盘并创建 `pending` 行；pytest 覆盖拒类型/超限/越权
- [x] 4.2 实现解析+切分服务（pdf/docx/md），单元测试用夹具文件断言抽出非空文本与 chunk 数量 ≥ 1；无法抽文本时进入失败路径
- [x] 4.3 实现异步 ingest（BackgroundTasks）：embed → 写入 `kb_{id}` collection → 状态 `ready`/`failed`；pytest 用假 Embedding 跑通状态机；`GET` 文档状态接口可轮询
- [x] 4.4 实现文档删除 API：删元数据、文件与该 document 的向量 ids；测试删除后检索不到该文档片段

## 5. 检索工具与出题路由

- [x] 5.1 实现 `kb_retrieve`（及可选 list-ready）工具：按 `knowledge_base_id` + 用户过滤检索；单测断言不会跨库/跨用户返回
- [x] 5.2 改造 `gather_research_context` / `generate_quiz`：无就绪库→仅 Tavily；有就绪库→Tavily+KB 工具；传入 `knowledge_base_id`→仅 KB 且空结果明确失败；pytest 用 stub tools 覆盖三种分支
- [x] 5.3 新增材料优先 Prompt 变体并接到 KB grounded 出题；单测或快照断言 system 提示含「材料优先/少编造」类约束
- [x] 5.4 扩展 `QuizGenerateRequest` / `QuizTaskCreateRequest` 可选 `knowledge_base_id`；异步任务持久化该字段；既有无该字段的请求契约测试仍通过

## 6. 前端知识库与开局

- [x] 6.1 重做 `pages/bank`：真实列表、空态、创建库；对接列表/创建 API；登录失败有提示（人工点验 + 关键请求路径）
- [x] 6.2 新增库详情页：文档列表、状态轮询、删除；`chooseMessageFile`（extension 无点）+ `uploadFile` 上传；超限/失败 toast 可读
- [x] 6.3 详情页「开始闯关」：校验至少一份 ready → 调 `/quiz/tasks` 带 `knowledge_base_id` → 复用现有 generate 轮询进入 quiz；空库不可开局
- [x] 6.4 首页出题请求保持不传 `knowledge_base_id`；可选更新 loading 文案；回归：无库用户仍能文本开局

## 7. 集成验收

- [x] 7.1 后端相关 pytest 全绿（含 KB API、ingest 状态机、出题三分支）
- [x] 7.2 手工主路径：建两个库分别上传不同领域文档 → 从库 A 开局题目不串到库 B；首页无库时行为接近原联网出题（用户确认主路径 OK；细节优化转 optimize-kb-drill-mode）
- [x] 7.3 对照 Context7/官方文档复核实现中的 `langchain-chroma`、`create_agent` 工具绑定、Taro `uploadFile`/`chooseMessageFile` 用法无过时 API

## Workflow follow-up

- 实现完成后按项目流程 archive 本 change，并将 delta specs 同步进主 specs。
- Archive 前确认 `.env` 中 `DASHSCOPE_API_KEY` 已由人工配置（若需真机入库联调）。
- 开发库执行 Alembic：`cd backend && alembic upgrade head`
