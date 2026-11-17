# Spec Delta

## ADDED Requirements

### Requirement: Document binaries persist via object storage keys

知识库文档的二进制内容 MUST 经对象存储能力持久化；文档元数据中的 `storage_path` MUST 表示存储 object key（相对键），供服务端入库与解析读取。客户端文档列表与详情 MUST NOT 暴露可匿名下载原文的公网直链。

#### Scenario: Upload persists binary under storage key

- **WHEN** 用户向自己的知识库成功上传合法文档
- **THEN** 系统 MUST 将文件内容写入对象存储，并在文档记录中保存对应 `storage_path` key，且后续异步入库 MUST 能依据该 key 读取正文

#### Scenario: API does not expose anonymous document download URL

- **WHEN** 客户端查询知识库文档列表或文档详情
- **THEN** 响应 MUST NOT 包含可供匿名公网直接下载该文档原文的 URL 字段

## MODIFIED Requirements

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
- **THEN** 系统 MUST 删除该库下文档元数据、对应向量数据以及文档二进制存储对象，且后续不可再对该库开局

### Requirement: Single document replace clears prior materials

每个知识库 MUST 在业务上按「一库一份文档」运作：当库内已有文档时再次上传，系统 MUST 替换旧文档（删除旧文档元数据、向量与存储对象，并清除该库学透要点地图与覆盖记录若存在），再入库新文档；MUST NOT 在同一库中堆积多份并行就绪正文作为合订本。

#### Scenario: Reupload replaces existing document

- **WHEN** 用户向已有文档的知识库上传新的合法文件
- **THEN** 系统 MUST 清除旧文档及其向量与存储对象（及学透地图/覆盖若有），并以新文件创建处理中文档继续入库

#### Scenario: Library name can follow new file stem

- **WHEN** 替换上传使用带扩展名的文件名
- **THEN** 系统 MAY 将知识库显示名更新为文件主名，且 MUST 保持库身份不变
