# Design

## Context

See `proposal.md` — Why。当前实现：

- 头像：`backend/app/routers/me.py` 写 `UPLOAD_DIR/avatars/`，`avatar_url` 为 `/uploads/avatars/...`，`main.py` 挂载 `StaticFiles`。
- 题库：`knowledge_service` / `master_map_service` 用 `knowledge_upload_root() / storage_path` 读写本地文件；`extract_text` 只接受 `Path`。
- 前端：`resolveAvatarUrl` 已兼容 `http(s)://`；上传仍是 `Taro.uploadFile` → 后端 multipart。
- 桶：`zzt-wwcg`，endpoint `oss-cn-hangzhou.aliyuncs.com`，无自定义域名；用户将自行填写 AccessKey。

官方依据：

- Bucket Policy 可对指定前缀授权匿名 `GetObject`（[OSS Bucket Policy](https://help.aliyun.com/zh/oss/user-guide/oss-bucket-policy/)）；匿名鉴权先看 Policy 再看 ACL（[鉴权流程](https://help.aliyun.com/zh/oss/user-guide/authentication)）。
- Python SDK：`alibabacloud-oss-python-sdk-v2`（Context7 `/aliyun/alibabacloud-oss-python-sdk-v2`）— `Client` + `put_object` / `get_object` / `delete_object`；默认凭证环境变量 `OSS_ACCESS_KEY_ID` / `OSS_ACCESS_KEY_SECRET`。

## Goals / Non-Goals

**Goals:**

- 统一 `ObjectStorage` 抽象（local | oss），业务只依赖 put / get / delete / public_url。
- 头像永久公网 URL；题库私有 key；替换/删除清理对象。
- 上传 API 与入库/拆题/出题契约不变；pytest 无 OSS 凭证时走 local。

**Non-Goals:**

- 存量 `uploads/` 迁移；STS 直传；CDN/自定义域名；签名 URL；改前端上传协议。

## Decisions

### 1. 访问模型 = 方案 C（桶私有 + 前缀 Policy）

| 前缀 | 匿名读 | 读方 |
|------|--------|------|
| `avatars/*` | 是（Bucket Policy） | 小程序/浏览器直接 HTTPS |
| `knowledge/*` | 否 | 仅服务端 AK |

**运维必做（应用外）：**

1. 将桶 ACL 从「公共读」改为 **私有**（否则整桶仍可匿名读，Policy 无法单独「关」掉 `knowledge/*`）。
2. 添加 Bucket Policy（将 `<UID>` 换成账号 UID）：

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": ["*"],
      "Action": ["oss:GetObject"],
      "Resource": ["acs:oss:*:<UID>:zzt-wwcg/avatars/*"]
    }
  ]
}
```

只授 `GetObject`，不授 `ListObjects` / 写权限。

**为何不用签名 URL：** 头像需永久展示；签名有时效。公网 URL + Policy 无过期问题。题库不给前端直链，无需签名。

**备选否决：** 整桶公共读（题库可猜 key 下载）；对象级 ACL 仅头像 public-read（也可用，但与用户选定的 C 策略一致时以 Policy 为准）。

### 2. SDK 选用 `alibabacloud-oss-python-sdk-v2`

```python
import alibabacloud_oss_v2 as oss

cfg = oss.config.load_default()
cfg.credentials_provider = oss.credentials.EnvironmentVariableCredentialsProvider()
cfg.region = "cn-hangzhou"
# 显式 endpoint 与现有控制台一致时：
cfg.endpoint = "https://oss-cn-hangzhou.aliyuncs.com"
client = oss.Client(cfg)

client.put_object(oss.PutObjectRequest(bucket=..., key=..., body=data, content_type=...))
result = client.get_object(oss.GetObjectRequest(bucket=..., key=...))
# result.body.read() / iter_bytes；用后关闭
client.delete_object(oss.DeleteObjectRequest(bucket=..., key=...))
```

**备选否决：** 旧包 `oss2` 仍可用，但官方主推 v2，Context7 文档更全；本期统一 v2。

### 3. 抽象与 key 约定

```
ObjectStorage
  put(key, data, content_type) -> None
  get(key) -> bytes
  delete(key) -> None          # 缺失视为成功
  public_url(key) -> str       # 仅头像展示用；local 返回 /uploads/... 相对路径
```

- 头像 key：`avatars/{user_id}_{uuid8}{ext}`
- 题库 key：`knowledge/{user_id}/{kb_id}/{doc_id}_{safe_filename}`（与现相对路径形态对齐，便于阅读）
- `avatar_url`：OSS 下 `https://zzt-wwcg.oss-cn-hangzhou.aliyuncs.com/{key}`；local 下仍 `/uploads/{key}`（保留 StaticFiles 挂载）。
- `storage_path`：始终存 key（OSS 与 local 同一套相对 key）。

工厂：`get_object_storage(settings)` — 当 `OSS_ACCESS_KEY_ID`、`OSS_ACCESS_KEY_SECRET`、`OSS_BUCKET`、以及 `OSS_ENDPOINT` 或 `OSS_REGION` 齐全时返回 `OssObjectStorage`，否则 `LocalObjectStorage(upload_dir)`。

### 4. 业务接入点（逻辑不变，换 IO）

| 位置 | 改动 |
|------|------|
| `me.upload_avatar` | put 新 key → 写完整/相对 URL → best-effort delete 旧 key（从旧 URL 解析） |
| `knowledge_service` 上传 | put key，写 `storage_path` |
| `_delete_doc_file` / purge / 删库 | `storage.delete(key)` |
| `run_ingest_document` / master map | `get(key)` → 临时文件 → 现有 `extract_text(Path)`（少改解析层） |

上传失败：抛出既有 `bad_request` / 5xx 风格可读错误（如 `STORAGE_ERROR`），不落「假成功」就绪态。

### 5. 配置

`.env` / `.env.example`（密钥留空由用户填）：

```
OSS_ACCESS_KEY_ID=
OSS_ACCESS_KEY_SECRET=
OSS_BUCKET=zzt-wwcg
OSS_ENDPOINT=https://oss-cn-hangzhou.aliyuncs.com
OSS_REGION=cn-hangzhou
```

`Settings` 增加对应字段。注意：v2 的 `EnvironmentVariableCredentialsProvider` 在 `OSS_ACCESS_KEY_*` 为空时**构造即抛** `CredentialsEmptyError`。因此工厂 MUST 先判断配置齐全再创建 OSS 客户端，并优先用 `StaticCredentialsProvider(settings 中的 id/secret)` 注入，避免「未配 OSS 却误触 SDK 构造」导致进程/请求异常；未齐全则直接走 Local。

### 6. 前端与小程序

- 上传链路不变；`avatar_url` 变 https 后现有 `resolveAvatarUrl` 直接透传。
- 微信公众平台配置 **downloadFile / 图片** 合法域名：`zzt-wwcg.oss-cn-hangzhou.aliyuncs.com`（实现任务中写清，属配置项非代码）。

### 7. 测试策略

- 单测默认不配 OSS → LocalObjectStorage；现有上传/入库用例尽量少改。
- 新增 storage 单元测试：local put/get/delete；OSS 客户端可用 mock Client。
- 头像用例断言：local 下仍以 `/uploads/avatars/` 开头；可选标记测试在集成环境验 https。

## Risks / Trade-offs

- [桶仍为公共读] → 题库可被匿名 GET。Mitigation：任务与文档明确要求改私有 + Policy；上线前用匿名 curl 验 `knowledge/` 403、`avatars/` 200。
- [旧头像仍是 `/uploads/...`] → 仅本机 StaticFiles 有效。Mitigation：不迁存量；用户重新上传即切 OSS URL。
- [临时文件盘 IO] → 入库多一次落盘。Mitigation：接受，换取不改 `extract_text`；后续可再支持 bytes。
- [删除旧对象失败] → 残留垃圾。Mitigation：best-effort + 日志；不阻断主流程。
- [微信未配 download 域名] → 真机头像不显示。Mitigation：tasks 列出域名配置检查项。

## Migration Plan

1. 控制台：桶改私有 → 加 `avatars/*` Policy → 填 `.env` 凭证。
2. 部署含 storage 抽象的后端；冒烟：上传头像（浏览器能开 URL）、上传题库（匿名打 knowledge URL 应失败）、入库成功。
3. 回滚：清空 OSS 凭证即可回退 local（新对象只在当时后端）；已写 OSS 的 URL/key 在回退后需重新上传或暂时不可用——接受「仅新上传」策略。

## Open Questions

无（方案 C、永久 URL、local 回退、不迁存量均已确认）。
