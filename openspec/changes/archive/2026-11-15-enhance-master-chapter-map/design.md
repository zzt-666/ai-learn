# Design

## Context

See proposal.md — Why。刷题路径已有 `kb_questions` + practice；学透仍走 Chroma Top‑K（约 900/120，`k=6`）生成题。产品已定一库一份文档、替换入库。方案基准：`docs/学透模式章节地图方案设计.md`。

## Goals / Non-Goals

**Goals:**

- MySQL 持久化章节/要点与用户覆盖；开局未覆盖优先取样再生成题。
- 结构优先切分 + 异步地图；失败可降级旧 RAG；替换/改刷题级联清理。
- 详情进度与复习轮 UX；单局 Prompt 只带选中要点 + 可选少量补片段。

**Non-Goals:**

- 独立 Rerank、OCR、多文档合订本。
- 要点只存小程序 Storage 或只塞 Chroma metadata。
- 刷题抽题改造；「一次塞全文」当覆盖方案。
- 交卷正确率加权覆盖（可 P2）。

## Decisions

1. **主缓存 = MySQL，Chroma 仅补检索**  
   需要精确列表、轮转、进度；与 `kb_questions` 对称。否决「要点只进 Chroma」。

2. **表结构**  
   - `kb_master_sections`：库/文档、ordinal、title、summary、可选 source_span  
   - `kb_master_points`：section、库冗余 FK、ordinal、title、summary、keywords_json、is_active  
   - `kb_master_point_coverage`：`(user_id, point_id)` 唯一；seen_count、last_seen_at  
   - 文档或库字段：`master_map_status`（pending/ready/failed）、`master_map_error`、可选 `master_point_count`

3. **生成时机**  
   学透向量入库成功后异步生成地图。未就绪开局：降级旧 Top‑K 并明示，或阻断（实现选一种主路径：默认允许降级 + 文案）。失败可 `POST .../master-map/rebuild`。

4. **切分**  
   标题/`第 x 章`/`##` → section；否则段落聚合约 800–1500 字/节。节内模型抽 2–8 要点；单库上限约 ≤80。

5. **开局取样**  
   `M = min(总要点, max(2, ceil(N/2)))`（实现期可微调）。未覆盖优先；否则 `last_seen_at` 最久。全覆盖 → ConfirmModal：复习 / 重置 / 取消。开局成功即写 coverage。

6. **补检索**  
   用选中要点文案 query Chroma `k=3~4` 贴 Prompt（可选）；不再以整库固定线索 Top‑6 为唯一来源。

7. **API**  
   - `GET .../master-status`：状态、计数、未覆盖、是否复习提示  
   - `POST .../master-map/rebuild`  
   - `POST .../reset-master-coverage`  
   - 现有 `POST /quiz/tasks` 学透分支改取样（前端可透明）  
   错误码：`MASTER_MAP_PENDING`、`MASTER_MAP_FAILED`、`MASTER_EMPTY`

8. **级联**  
   替换文档 / 删库 / 改刷题：清 sections、points、coverage；刷题管道按现有 confirm-mode。

**Alternatives considered:** 只加大 Top‑K / Rerank（拒：不解决结构化覆盖）；覆盖只记前端（拒：换机丢失）。

## Risks / Trade-offs

- [无标题讲义切章不准] → 段落聚合 + 重建地图  
- [生成贵/慢] → 要点上限、异步、降级旧 RAG  
- [开局即记 seen 可能「刷进度」] → 接受防弃局重复；P2 可加正确权重  
- [与旧 Top‑K 行为差] → 详情标明覆盖学透；降级明示  

## Migration Plan

1. Alembic 三表 + status 列。  
2. 已有学透库：详情进入或下次 ingest 触发 rebuild；未 ready 前旧开局。  
3. 回滚：开局忽略地图，恢复 `k=6` 强制检索。

## Open Questions

- 本局 M 与 N 公式微调（不挡开干）。  
- 详情是否展示只读章节列表（可选）。  
- 地图 pending 时默认「允许降级开局」还是「禁用直至 ready」（推荐：允许降级 + 文案）。
