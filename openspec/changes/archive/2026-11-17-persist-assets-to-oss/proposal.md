# Proposal

## Why

头像与题库文档目前落在服务端本地 `uploads/`，进程/磁盘漂移后易丢、也不利于多实例部署。题库优化文档已将「文档存 OSS」列为与业务解耦的 P2；现在要把这两类二进制持久化到已有阿里云 OSS 桶，同时把头像做成永久公网可读、题库保持私有。

## What Changes

- 引入统一的对象存储抽象（本地 / OSS 可切换）：上传、按 key 读取、删除；业务层不再直接写死本地路径。
- **头像**：`POST /api/v1/me/avatar` 仍走服务端 multipart；对象写入桶前缀 `avatars/`；`users.avatar_url` 存**永久公网 HTTPS URL**（非签名 URL）；替换头像时删除旧对象。
- **题库文档**：上传/替换/删除/入库读文件链路不变；`knowledge_documents.storage_path` 存 **OSS object key**（前缀 `knowledge/`）；仅服务端用 AK 读写；前端不提供文档直链。
- 桶侧采用方案 C：Bucket ACL **私有** + Bucket Policy 仅对 `avatars/*` 允许匿名 `GetObject`；`knowledge/*` 保持私有。
- 环境变量与 `.env.example` 补齐 OSS 配置；凭证由部署者填写。
- **仅新上传进 OSS**；不迁移存量本地文件。
- **不做**：STS 客户端直传、自定义域名/CDN、签名 URL、改上传 API 契约、改拆题/学透/出题逻辑。

## Capabilities

### New Capabilities

- `object-storage`: 统一对象存储（put/get/delete）、头像公网永久 URL 与题库私有对象约定、OSS/本地后端选择与配置失败可读错误、替换/删除时清理对象。

### Modified Capabilities

- `knowledge-base`: 明确文档二进制经对象存储持久化；`storage_path` 为存储 key；文档内容不对匿名公网开放；删除/替换时同步删除存储对象。

## Impact

- **后端**：新增 storage 模块与配置项；`me` 头像上传、`knowledge_service` / `master_map_service` 读写删改为经抽象层；依赖 `alibabacloud-oss-python-sdk-v2`；pytest 在未配 OSS 时走本地后端。
- **API**：路径与请求体不变；头像响应中 `avatar_url` 从相对 `/uploads/...` 变为完整 `https://...`（前端 `resolveAvatarUrl` 已支持 https）。
- **前端（Taro）**：上传接口不变；小程序需将 OSS 域名加入 downloadFile / 图片合法域名（`zzt-wwcg.oss-cn-hangzhou.aliyuncs.com`）。
- **运维**：桶 `zzt-wwcg`、endpoint `oss-cn-hangzhou.aliyuncs.com`；需将桶改为私有并配置 `avatars/*` 公共读策略（见 design）。
- **不动**：JWT、入库/拆题/要点地图/出题契约、Chroma、EXP 结算。
