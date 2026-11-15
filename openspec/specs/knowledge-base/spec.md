# knowledge-base Specification

## Purpose

让已登录用户创建多个命名私有知识库、上传 pdf/docx/markdown 并完成入库，以便按库隔离检索并支持材料优先的闯关学习。

## Requirements

### Requirement: User can manage multiple named knowledge bases

系统 MUST 允许已登录用户创建、重命名、列出与删除仅属于自己的命名知识库；不同知识库彼此隔离，开局时只能针对用户选定的一个知识库检索。

#### Scenario: Create a knowledge base

- **WHEN** 已登录用户提交合法非空名称创建知识库
- **THEN** 系统 MUST 创建属于该用户的知识库并在列表中返回

#### Scenario: List only own knowledge bases

- **WHEN** 已登录用户请求知识库列表
- **THEN** 系统 MUST 仅返回该用户拥有的知识库，不得返回他人的库

#### Scenario: Delete knowledge base removes its documents

- **WHEN** 用户删除某一知识库
- **THEN** 系统 MUST 删除该库下文档元数据与对应向量数据，且后续不可再对该库开局

### Requirement: User can upload supported documents into a knowledge base

系统 MUST 允许用户向自己拥有的知识库上传 **pdf、docx、markdown（.md）** 文件；不支持的类型 MUST 被拒绝并返回可读错误。

#### Scenario: Upload PDF into owned knowledge base

- **WHEN** 用户向自己的知识库上传合法 pdf 文件
- **THEN** 系统 MUST 接受上传并创建文档记录，初始状态为处理中或等价可轮询状态

#### Scenario: Reject unsupported file type

- **WHEN** 用户上传非 pdf/docx/md 的文件
- **THEN** 系统 MUST 拒绝入库并返回可读错误，且不得写入向量库

#### Scenario: Cannot upload into another user's knowledge base

- **WHEN** 用户尝试向不属于自己的知识库上传文档
- **THEN** 系统 MUST 拒绝（如 404/403）且不创建文档

### Requirement: Documents are ingested asynchronously with visible status

上传成功后，系统 MUST 异步完成解析、切分与向量化；客户端 MUST 能查询文档状态（处理中 / 就绪 / 失败）。失败时 MUST 提供可读原因，且该文档 MUST NOT 参与检索出题。学透模式库在向量化成功后 MUST 继续触发要点地图生成流水线（地图细节见 master-chapter-map）。

#### Scenario: Successful ingest becomes ready

- **WHEN** 文档解析与向量化成功完成
- **THEN** 文档状态 MUST 变为就绪，并可用于该知识库的检索出题

#### Scenario: Failed ingest is visible and excluded from retrieval

- **WHEN** 解析或向量化失败
- **THEN** 文档状态 MUST 为失败并带可读原因，且检索 MUST NOT 使用该文档内容

#### Scenario: Master ingest queues chapter map

- **WHEN** 学透模式知识库文档向量化成功
- **THEN** 系统 MUST 排队或启动要点地图生成，不得在无后续任务的情况下结束学透 ingest 链路

### Requirement: Knowledge base quiz entry requires ready content

仅当目标知识库至少有一份就绪文档时，系统才允许从该库发起闯关；否则 MUST 给出可读提示，禁止空库出题。

#### Scenario: Start quiz from knowledge base with ready documents

- **WHEN** 用户从题库 Tab 选择一个至少含一份就绪文档的知识库并开始闯关
- **THEN** 系统 MUST 允许进入出题流程，且出题检索范围限定为该知识库

#### Scenario: Block quiz from empty or not-ready knowledge base

- **WHEN** 用户选择的知识库没有任何就绪文档
- **THEN** 系统 MUST 拒绝开局并提示用户先上传或等待入库完成

### Requirement: Bank tab manages knowledge bases

「题目」Tab MUST 提供知识库列表、创建入口、进入库详情（文档列表/上传/删除）以及从库开局的入口，不再仅展示无功能的占位列表。

#### Scenario: Bank tab shows real knowledge bases

- **WHEN** 已登录用户打开题目 Tab
- **THEN** 客户端 MUST 展示该用户真实知识库列表（可为空态），MUST NOT 仅展示与后端无关的假数据列表作为唯一内容

#### Scenario: Empty knowledge bases state

- **WHEN** 用户尚无任何知识库
- **THEN** 客户端 MUST 展示空态与创建引导，而不是静默无操作

### Requirement: Per-user isolation and login gate

知识库与文档的全部读写 MUST 要求登录，并按当前用户归属校验；未登录 MUST NOT 访问知识库能力。

#### Scenario: Unauthenticated access denied

- **WHEN** 未携带有效登录态的客户端请求知识库或文档接口
- **THEN** 系统 MUST 返回未授权错误

### Requirement: Reasonable upload limits

系统 MUST 对单文件大小与单库文档数量施加明确上限；超限 MUST 拒绝并返回可读错误。默认上限：单文件 ≤ 10MB；**每库同一时间最多保留 1 份就绪或处理中的文档**（再上传视为替换，见单文档替换要求）；每用户知识库 ≤ 10（实现可配置，但不得无上限）。

#### Scenario: Reject oversized file

- **WHEN** 用户上传超过大小上限的文件
- **THEN** 系统 MUST 拒绝保存并返回可读错误

#### Scenario: Reject when knowledge base document quota exceeded

- **WHEN** 目标知识库在不允许替换的路径下已达文档数量上限且用户再上传
- **THEN** 系统 MUST 拒绝上传并返回可读错误

### Requirement: Single document replace clears prior materials

每个知识库 MUST 在业务上按「一库一份文档」运作：当库内已有文档时再次上传，系统 MUST 替换旧文档（删除旧文档元数据与向量，并清除该库学透要点地图与覆盖记录若存在），再入库新文档；MUST NOT 在同一库中堆积多份并行就绪正文作为合订本。

#### Scenario: Reupload replaces existing document

- **WHEN** 用户向已有文档的知识库上传新的合法文件
- **THEN** 系统 MUST 清除旧文档及其向量（及学透地图/覆盖若有），并以新文件创建处理中文档继续入库

#### Scenario: Library name can follow new file stem

- **WHEN** 替换上传使用带扩展名的文件名
- **THEN** 系统 MAY 将知识库显示名更新为文件主名，且 MUST 保持库身份不变
