# Spec Delta

## MODIFIED Requirements

### Requirement: Reasonable upload limits

系统 MUST 对单文件大小与单库文档数量施加明确上限；超限 MUST 拒绝并返回可读错误。默认上限：单文件 ≤ 10MB；**每库同一时间最多保留 1 份就绪或处理中的文档**（再上传视为替换，见单文档替换要求）；每用户知识库 ≤ 10（实现可配置，但不得无上限）。

#### Scenario: Reject oversized file

- **WHEN** 用户上传超过大小上限的文件
- **THEN** 系统 MUST 拒绝保存并返回可读错误

#### Scenario: Reject when knowledge base document quota exceeded

- **WHEN** 目标知识库在不允许替换的路径下已达文档数量上限且用户再上传
- **THEN** 系统 MUST 拒绝上传并返回可读错误

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

## ADDED Requirements

### Requirement: Single document replace clears prior materials

每个知识库 MUST 在业务上按「一库一份文档」运作：当库内已有文档时再次上传，系统 MUST 替换旧文档（删除旧文档元数据与向量，并清除该库学透要点地图与覆盖记录若存在），再入库新文档；MUST NOT 在同一库中堆积多份并行就绪正文作为合订本。

#### Scenario: Reupload replaces existing document

- **WHEN** 用户向已有文档的知识库上传新的合法文件
- **THEN** 系统 MUST 清除旧文档及其向量（及学透地图/覆盖若有），并以新文件创建处理中文档继续入库

#### Scenario: Library name can follow new file stem

- **WHEN** 替换上传使用带扩展名的文件名
- **THEN** 系统 MAY 将知识库显示名更新为文件主名，且 MUST 保持库身份不变
