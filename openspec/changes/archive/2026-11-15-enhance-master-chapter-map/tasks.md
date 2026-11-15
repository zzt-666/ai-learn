# Tasks

## 1. Data model and cascade

- [x] 1.1 新增 Alembic 迁移：`kb_master_sections` / `kb_master_points` / `kb_master_point_coverage` 与文档或库上 `master_map_status` / `master_map_error` / 可选 `master_point_count`；`alembic upgrade head` 成功
- [x] 1.2 实现 ORM 与删除知识库、文档替换、改刷题模式时级联清理地图与覆盖；用单元/集成测试断言替换后旧 point 不可见且 coverage 清空

## 2. Structure split and map generation

- [x] 2.1 实现结构优先切分（标题/`第 x 章`/`##`）与段落聚合回退；单测覆盖有标题与纯散文样例
- [x] 2.2 实现异步要点地图生成（节内抽要点、单库上限、写 MySQL、更新 status）；向量成功后学透 ingest 排队该任务；失败置 failed 且文档仍 ready
- [x] 2.3 提供 `POST .../master-map/rebuild`；失败重试可将 status 从 failed 拉回 pending 并重新生成（接口测试通过）

## 3. Status API and coverage

- [x] 3.1 实现 `GET .../master-status`（状态、要点总数、已覆盖/未覆盖、是否复习提示）；归属校验失败返回 403/404
- [x] 3.2 实现开局取样（未覆盖优先，否则最久；全覆盖标记需复习）与 `POST .../reset-master-coverage`；单测覆盖取样优先级与重置范围

## 4. Master quiz path

- [x] 4.1 学透 `quiz/tasks`（或等价）在地图 ready 时按 M/N 公式取要点组装 Prompt，可选 Chroma k=3~4 补片段；禁止全文塞 Prompt；单测/契约测断言走要点路径
- [x] 4.2 地图 pending/failed 时降级旧检索并返回可感知标记/文案，或返回 `MASTER_MAP_*` 错误；开局成功后写入 coverage（seen）；测降级与 coverage 写入
- [x] 4.3 全覆盖开局前返回需复习信号；与刷题复习轮同构的前端 ConfirmModal：复习 / 重置 / 取消

## 5. Frontend (Taro)

- [x] 5.1 学透库详情展示「已覆盖 a / 共 b」、pending/failed 提示与重建入口；对接 master-status
- [x] 5.2 开局流程：题量保留；pending 时提示可降级；全覆盖弹复习轮；必要时列表短文案覆盖率
- [x] 5.3 编译 weapp 相关页无新增类型/引用错误（`npm`/`pnpm` 既有 build 或 tsc 检查通过）

## 6. Integration check

- [x] 6.1 跑相关 pytest（地图生成、取样、开局、替换清理）全部通过
- [x] 6.2 手工或脚本验收：同一学透库连续两局主要点集合重叠明显低于「固定线索 Top‑6」基线；替换文档后进度归零

## Workflow follow-up

- Archive `enhance-master-chapter-map` after implementation and review.
- Sync delta specs into main `openspec/specs/` on archive.
