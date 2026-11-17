# Spec Delta

## Purpose

为头像与题库文档提供统一的对象存储行为：可切换后端、按前缀隔离公开/私有访问，并在替换与删除时清理对象，避免业务逻辑绑定本地磁盘。

## ADDED Requirements

### Requirement: Unified object storage backend selection

系统 MUST 通过统一对象存储能力完成头像与题库文档的写入、按 key 读取与删除。当 OSS 凭证与桶配置齐全时 MUST 使用阿里云 OSS；未齐全时 MUST 回退本地磁盘后端，以便开发与自动化测试仍可运行。

#### Scenario: OSS configured uses cloud backend

- **WHEN** 环境中已配置可用的 OSS AccessKey、Secret、Bucket 与 Endpoint（或等价 Region）
- **THEN** 新上传的头像与题库文档 MUST 写入该 OSS 桶，不得仅写本地 `uploads/` 作为唯一持久化副本

#### Scenario: Incomplete OSS config falls back to local

- **WHEN** OSS 必要配置缺失或不完整
- **THEN** 系统 MUST 使用本地磁盘后端完成同等 put/get/delete 语义，且 MUST NOT 在启动时因缺少 OSS 而直接崩溃（业务请求仍可按本地路径工作）

### Requirement: Avatar stored as permanent public HTTPS URL

头像上传成功后，系统 MUST 将对象写入桶前缀 `avatars/`，并将 `users.avatar_url` 设为可永久访问的完整公网 `https://` URL（虚拟主机风格，无自定义域名时形如 `https://{bucket}.{endpoint}/{key}`）。MUST NOT 使用带过期时间的签名 URL 作为对外头像地址。

#### Scenario: Avatar upload returns permanent HTTPS URL

- **WHEN** 已登录用户通过现有头像上传接口成功上传合法图片
- **THEN** 响应中的 `avatar_url` MUST 为以 `https://` 开头的完整 URL，且在桶策略允许匿名读该对象时无需额外鉴权即可展示

#### Scenario: Avatar replace deletes previous object

- **WHEN** 用户再次上传头像且数据库中已有指向本系统对象的旧 `avatar_url` 或旧 object key
- **THEN** 系统 MUST 在写入新对象并更新 `avatar_url` 后尝试删除旧头像对象；删除失败 MUST NOT 阻断新头像生效，但 MUST 记录可观测日志

### Requirement: Knowledge documents are private object keys

题库文档对象 MUST 写入前缀 `knowledge/`；`knowledge_documents.storage_path` MUST 保存 object key（而非公网 URL）。系统 MUST NOT 向客户端返回可匿名下载题库原文的直链；入库、拆题、要点地图等服务端流程 MUST 仅通过具备凭证的存储读取能力获取正文。

#### Scenario: Upload stores object key not public URL

- **WHEN** 用户向知识库成功上传文档且 OSS 后端启用
- **THEN** 文档记录的 `storage_path` MUST 为 `knowledge/...` 形式的 object key，MUST NOT 为可匿名访问的完整 URL

#### Scenario: Ingest reads via authenticated storage access

- **WHEN** 文档进入异步解析/入库且二进制位于对象存储
- **THEN** 系统 MUST 通过带凭证的 get 读取该 key 的内容再解析；MUST NOT 依赖匿名公网 GET 获取题库正文

### Requirement: Delete and replace remove stored objects

删除知识库文档、替换库内唯一文档、或删除整个知识库时，系统 MUST 删除对应的存储对象（best-effort：对象已不存在视为成功）。对象存储失败导致无法完成写入时，系统 MUST 返回可读错误且 MUST NOT 将失败上传标记为已就绪。

#### Scenario: Document delete removes storage object

- **WHEN** 用户删除某一知识库文档且该文档有非空 `storage_path`
- **THEN** 系统 MUST 删除该 key 对应的存储对象（若不存在则视为已清理），并删除元数据与向量等既有连带数据

#### Scenario: Storage put failure is visible

- **WHEN** 头像或文档上传在写入对象存储阶段失败
- **THEN** 系统 MUST 向客户端返回可读错误，且 MUST NOT 将本次上传视为成功持久化

### Requirement: OSS configuration is explicit and documented

系统 MUST 通过环境变量暴露 OSS 相关配置（至少包含 AccessKey ID、AccessKey Secret、Bucket、Endpoint 或 Region），并在示例环境文件中给出占位项与桶名约定。配置错误（如凭证无效导致 put 失败）MUST 表现为业务可读错误，而非静默丢弃文件。

#### Scenario: Example env documents required OSS keys

- **WHEN** 部署者查看后端环境变量示例
- **THEN** 示例 MUST 包含填写 OSS AccessKey、Secret、Bucket、Endpoint/Region 的占位说明
