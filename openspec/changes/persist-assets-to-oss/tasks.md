# Tasks

## 1. Dependencies & configuration

- [ ] 1.1 在 `backend/requirements.txt` 增加 `alibabacloud-oss-python-sdk-v2`，安装后确认 `import alibabacloud_oss_v2` 成功
- [ ] 1.2 在 `Settings` 与 `backend/.env.example`（及本地 `.env` 占位）增加 `OSS_ACCESS_KEY_ID`、`OSS_ACCESS_KEY_SECRET`、`OSS_BUCKET=zzt-wwcg`、`OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com`、`OSS_REGION=cn-hangzhou`；密钥留空由部署者填写 — 核对示例文件含桶名与 endpoint 约定
- [ ] 1.3 实现 `is_oss_configured(settings)`：四要素（id/secret/bucket + endpoint 或 region）齐全才为真；单测覆盖「缺一项 → false」

## 2. Object storage abstraction

- [ ] 2.1 新增 `ObjectStorage` 协议与 `LocalObjectStorage`（根目录 `UPLOAD_DIR`，key 相对路径 put/get/delete；`public_url` 返回 `/uploads/{key}`）— 单元测试覆盖 put/get/delete 与缺失 delete 不抛
- [ ] 2.2 实现 `OssObjectStorage`：用 `StaticCredentialsProvider` + `Client`（region/endpoint 来自 Settings）实现 put/get/delete；`public_url` 返回 `https://{bucket}.oss-cn-hangzhou.aliyuncs.com/{key}`（或由 endpoint 推导的虚拟主机 URL）— 用 mock Client 单测调用参数
- [ ] 2.3 实现 `get_object_storage()` 工厂：配置齐全 → OSS，否则 Local；确认**不会**在未配密钥时构造会抛 `CredentialsEmptyError` 的 env provider — 单测两种分支

## 3. Avatar path

- [ ] 3.1 改造 `POST /api/v1/me/avatar`：经 storage put 到 `avatars/...`；OSS 时写完整 https `avatar_url`，Local 时写 `/uploads/...`；替换时解析旧 URL/key 并 best-effort delete — `test_avatar_upload_ok` 等用例在默认 Local 下通过，并断言 URL 形态
- [ ] 3.2 补充「替换头像会调用 delete 旧 key」的单测（可注入假 storage）— 验证新 URL 生效且 delete 被调用一次

## 4. Knowledge document path

- [ ] 4.1 改造文档上传：`storage_path` 仍为 `knowledge/{user}/{kb}/{doc}_{name}` key；内容 `storage.put`；失败返回可读错误且不留下「假就绪」— 现有 `test_upload_*` 在 Local 下通过
- [ ] 4.2 改造 `_delete_doc_file` / purge / 删库路径为 `storage.delete`；替换上传删除旧对象 — 单测或现有 replace/delete 用例确认 delete 被触发
- [ ] 4.3 改造 `run_ingest_document` 与 `master_map_service`：`storage.get` → 临时文件 → 现有 `extract_text(Path)`；用后清理临时文件 — 入库/学透地图相关测试在 Local 下通过

## 5. Docs, ops checklist & regression

- [ ] 5.1 在设计约定处（可短注释于 `.env.example` 或现有运维说明）写明：桶 ACL 改为私有；Bucket Policy 仅 `avatars/*` 匿名 `GetObject`；微信合法域名 `zzt-wwcg.oss-cn-hangzhou.aliyuncs.com` — 核对文档可按步骤操作
- [ ] 5.2 跑相关后端测试集（auth 头像、knowledge upload/ingest/delete/replace、master map 抽样）确认全绿
- [ ] 5.3（人工）填写真实 AK 后冒烟：头像 URL 匿名可开；`knowledge/` 对象匿名 GET 应失败；上传题库后入库成功

## Workflow follow-up

- Archive the change after implementation review is satisfied.
- Sync delta specs into main specs on archive when applicable.
