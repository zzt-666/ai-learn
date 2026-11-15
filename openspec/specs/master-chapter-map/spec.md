# master-chapter-map Specification

## Purpose

为学透模式知识库生成并持久化章节/要点地图，按用户记录覆盖进度，使多局开局能优先未覆盖要点并展示可解释的吃透进度。

## Requirements

### Requirement: Master map is generated after successful ingest

学透模式知识库在文档向量入库成功后，系统 MUST 异步生成章节与要点地图并持久化；地图状态 MUST 对客户端可见（pending / ready / failed）。地图生成失败 MUST NOT 单独把已就绪文档打回失败，但 MUST 暴露可读错误并允许重试重建。

#### Scenario: Map becomes ready after master ingest

- **WHEN** 学透库文档解析与向量化成功完成
- **THEN** 系统 MUST 启动或排队地图生成，并在成功后将地图状态置为 ready，且该库具备可查询的章节与要点

#### Scenario: Map failure keeps document ready

- **WHEN** 地图生成失败而向量入库已成功
- **THEN** 文档 MUST 仍为就绪；地图状态 MUST 为 failed 并带可读原因；用户 MUST 能触发重建地图

### Requirement: Structure-first sectioning with character fallback

系统 MUST 优先按标题/章节结构切分文档生成章节节点；无可用结构时 MUST 回退为段落聚合的字符切分。每个章节 MUST 产出有限数量的要点（含短标题与摘要），且单库要点总数 MUST 有明确上限以防爆表。

#### Scenario: Headed document yields titled sections

- **WHEN** 材料含可识别章节标题（如 Markdown 标题或「第 x 章」）
- **THEN** 系统 MUST 按标题形成有序章节，并在各节内生成要点

#### Scenario: Prose document uses paragraph aggregation

- **WHEN** 材料无明显章节标题
- **THEN** 系统 MUST 按段落聚合形成有序章节并生成要点，不得因无标题而跳过地图生成

### Requirement: Coverage is tracked per user and point

系统 MUST 按用户与要点持久化覆盖记录（至少含进入含该点之局的次数与最近时间）。开局取样 MUST 优先未覆盖要点；全覆盖时 MUST 支持复习轮提示与用户确认后的覆盖重置。系统 MUST NOT 将学透覆盖记入刷题练习表。

#### Scenario: Prefer uncovered points when starting

- **WHEN** 学透地图已 ready 且用户发起开局
- **THEN** 系统 MUST 优先选择未见过或覆盖次数为 0 的要点组装本局依据

#### Scenario: Full coverage offers review or reset

- **WHEN** 该用户在本库已无未覆盖要点且尝试开局
- **THEN** 系统 MUST 提示本库要点已过一轮，并提供复习轮、重置覆盖（需确认）或取消；MUST NOT 在无提示下把已覆盖点伪装为全新内容

#### Scenario: Reset clears only that user's coverage

- **WHEN** 用户确认重置本库学透覆盖
- **THEN** 系统 MUST 清空该用户在该库的要点覆盖记录，且 MUST NOT 删除章节/要点地图本身

### Requirement: Client can read master map progress

系统 MUST 提供可读的学透地图状态与进度（至少：地图状态、要点总数、当前用户已覆盖数或等价覆盖率）。学透库详情 MUST 展示上述进度；地图 pending 或 failed 时 MUST 有明确提示。

#### Scenario: Detail shows coverage counts

- **WHEN** 用户打开学透模式且地图 ready 的知识库详情
- **THEN** 客户端 MUST 能展示已覆盖要点数与总要点数（或等价进度）

#### Scenario: Pending map is visible before start

- **WHEN** 地图仍为 pending
- **THEN** 客户端 MUST 提示要点地图生成中，且不得假装已完整覆盖学透

### Requirement: Replace and mode switch clear master map data

当学透库文档被替换，或库模式改为刷题时，系统 MUST 清除该库旧要点地图与相关覆盖记录（或等价失效），再按新内容/新模式重建或停用。删除知识库时 MUST 一并清除地图与覆盖数据。

#### Scenario: Document replace purges old map

- **WHEN** 用户向已有文档的学透库再次上传并完成替换
- **THEN** 系统 MUST 清除旧章节/要点与覆盖记录，并在新文档入库后重新生成地图

#### Scenario: Switch to drill clears master map

- **WHEN** 用户将知识库模式从学透改为刷题并生效
- **THEN** 系统 MUST 停用或清除学透地图与覆盖，后续 MUST NOT 再按旧要点开局
