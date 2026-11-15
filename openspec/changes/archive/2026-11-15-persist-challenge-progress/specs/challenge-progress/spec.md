# Spec Delta

## Purpose

让已登录用户在闯关中途退出后仍可恢复未完成进度，并在答完全部题目但未查看报告时静默通关入库，避免浪费已生成题目且保证历史可回看报告。

## ADDED Requirements

### Requirement: In-progress challenge progress is persisted server-side

出题成功进入闯关后，系统 MUST 将本局题目、主题、来源文本、已作答列表与当前题号持久化到服务端，并与当前登录用户绑定。中途退出、杀进程或本地缓存丢失 MUST NOT 导致服务端进度丢失。

#### Scenario: Progress saved after answering a question

- **WHEN** 用户在闯关中提交一题答案（判题完成）
- **THEN** 系统 MUST 将该题作答与更新后的当前进度写入该用户的服务端进行中会话

#### Scenario: Progress survives app exit mid-challenge

- **WHEN** 用户已答部分题目后退出闯关页或关闭小程序，之后再次打开并请求恢复该局
- **THEN** 系统 MUST 能返回同一局的题目与已作答进度，供客户端继续作答

### Requirement: User can resume an unfinished challenge from history

历史闯关列表 MUST 展示属于当前用户的未完成会话，并与已通关会话可区分。用户点击未完成项时，系统 MUST 恢复该局题目与进度并进入答题流程，从可继续的题号接着答，MUST NOT 重新生成题目。

#### Scenario: Unfinished item appears in history

- **WHEN** 用户有至少一局进行中且尚未答完所有题的会话
- **THEN** `GET` 历史列表 MUST 包含该会话，且状态标识为未完成（非已通关）

#### Scenario: Resume from unfinished history item

- **WHEN** 用户点击一条未完成历史记录并选择继续闯关
- **THEN** 客户端 MUST 加载该会话的题目与已有答案，进入答题页并定位到应继续的题号

#### Scenario: Completed item still opens report

- **WHEN** 用户点击一条已通关历史记录
- **THEN** 系统行为 MUST 仍允许查看该局报告（与既有历史回看一致）

### Requirement: Answering all questions without opening report still completes the challenge

当用户已对全部题目完成作答，但未点击「查看报告」或未停留在报告页就返回时，系统 MUST 将该局视为通关：结算奖励、持久化通关记录，并静默生成答题报告。用户之后 MUST 能在历史闯关记录中查看该报告。

#### Scenario: Leave after last answer without viewing report

- **WHEN** 本局所有题目均已作答，用户未进入报告页即离开闯关流程
- **THEN** 系统 MUST 将该会话标记为已通关（或等价完成态），MUST 结算本局 EXP/积分，并 MUST 异步或后台生成报告后可供历史回看

#### Scenario: History shows completed silent finish

- **WHEN** 上述静默通关已完成入库
- **THEN** 历史列表 MUST 展示该局为已通关，用户打开后 MUST 能读取报告内容

#### Scenario: Partial progress is not treated as completed

- **WHEN** 用户中途退出且仍有未作答题目
- **THEN** 系统 MUST NOT 将该局标记为已通关，MUST NOT 结算通关奖励，MUST 保留为可继续的未完成会话

### Requirement: Starting a new challenge does not erase other unfinished sessions

用户新开一局闯关时，系统 MUST NOT 删除或覆盖该用户其他未完成会话在服务端的进度。新局 MUST 使用独立会话标识。

#### Scenario: New quiz keeps previous unfinished session

- **WHEN** 用户已有一局未完成会话，又成功出题并开始新的一局
- **THEN** 系统 MUST 保留原未完成会话，且新局 MUST 有独立会话 id，用户仍可从历史继续旧局

### Requirement: Home shows up to three unfinished challenges in sync with history

首页 MUST 展示当前用户未完成闯关的预览区，数据与历史中的未完成会话同源（同一服务端集合与排序）。首页最多展示 3 条；超出部分 MUST 仅在闯关历史页查看。每条未完成项右侧 MUST 用进度条展示已闯进度（已作答题数相对总题数）。无未完成时 MUST 展示提示语，MUST NOT 伪造未完成条目。

#### Scenario: Home caps unfinished list at three

- **WHEN** 用户有超过 3 局未完成会话
- **THEN** 首页 MUST 仅展示按同源排序的前 3 条，其余 MUST 可在历史页看到

#### Scenario: Home empty state when no unfinished

- **WHEN** 用户没有任何未完成会话
- **THEN** 首页未完成区 MUST 展示提示语，且 MUST NOT 展示伪造成绩或虚假进度条

#### Scenario: Progress bar reflects answered ratio

- **WHEN** 首页展示一条未完成闯关且该局已答 k 题、共 N 题（0 ≤ k < N）
- **THEN** 该条目右侧进度条 MUST 反映 k/N 的进度

#### Scenario: Home syncs after resume-complete from history

- **WHEN** 用户在历史页续玩某未完成局并完成全部答题（含静默通关），之后再次进入或刷新首页
- **THEN** 该局 MUST 不再出现在首页未完成列表，且首页未完成集合 MUST 与历史中仍未完成的会话一致
