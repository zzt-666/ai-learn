# OpenSpec 使用教程（傻瓜版）

面向本项目（`AI-learn`）的超简说明。目标：先和 AI 说清楚要做什么，再让它写代码。

官方仓库：[Fission-AI/OpenSpec](https://github.com/Fission-AI/OpenSpec)

---

## OpenSpec 是啥？

一句话：**先和 AI 说清楚要做什么，再让它写代码。**

不装的时候：你说一句「加个功能」，AI 直接开写，容易跑偏。  
装了之后：先出一份「说明书」（proposal / specs / tasks），你改对了再写代码。

---

## 整体就 5 步（死记这个循环）

```text
想清楚 → 出方案 → 你改方案 → AI 写代码 → 归档
 Explore    Propose    Review      Apply       Archive
```

---

## 第 0 步：安装（只做一次）

你是 Windows，在 **PowerShell** 里执行：

```powershell
irm https://openspec.dev/cli/install.ps1 | iex
```

装完检查：

```powershell
openspec --version
```

能看到版本号就对了。

> 备选（需要 Node ≥ 22.12）：`npm install -g @fission-ai/openspec@latest`

---

## 第 1 步：在项目里初始化（每个项目一次）

在项目根目录：

```powershell
cd d:\Python_Study\AI-learn
openspec init
```

它会问你用什么 AI 工具——选 **Cursor**（或你实际在用的）。

完成后大概会有：

```text
openspec/
├── config.yaml    # 项目说明给 AI 看
├── specs/         # 已完成功能的「说明书」
└── changes/       # 正在做的功能
    └── archive/   # 做完的功能会挪到这里
```

IDE 里如果看不到新技能，**重启一下 Cursor**。

---

## 第 2 步：开始加功能（日常就用这个）

### ① 想清楚（可选，但推荐）

在 Cursor 聊天里说：

```text
帮我探索一下：我想给这个项目加「错题本」功能，先别写代码，先看看现有结构，给我几个方案。
```

或用技能：`/openspec-explore`

AI 只讨论方案，**不写代码**。

---

### ② 出方案（Propose）

想法清楚后说：

```text
Propose a change to add 错题本功能
```

或：`/openspec-propose add-wrong-book`

AI 会生成类似：

```text
openspec/changes/add-wrong-book/
├── proposal.md   # 为什么做、改什么
├── specs/        # 怎样算做完（验收标准）
├── design.md     # 技术怎么做（有时才有）
└── tasks.md      # 具体任务清单
```

**这时还没有任何业务代码。**

---

### ③ 你检查方案（最重要）

按这个顺序看：

1. `proposal.md` — 是不是你要的那个问题？范围会不会太大？
2. `specs/` — 这些要求做成了，你认不认？
3. `tasks.md` — 任务有没有漏、有没有多余？

不对就直接说，例如：

```text
规格里漏了：未登录不能看错题本。请改一下。
```

或自己改这些 Markdown 文件。

---

### ④ 让 AI 写代码（Apply）

建议：**新开一个干净对话**，然后：

```text
Apply the add-wrong-book change.
```

或：`/openspec-apply-change`

AI 会按 `tasks.md` 一项项做，做完勾选。  
中断了？再开对话说同一句，它会从**没勾的任务**继续。

---

### ⑤ 归档（Archive）

`tasks.md` 全勾完后说：

```text
Archive the add-wrong-book change.
```

或：`/openspec-archive-change`

效果：

- 需求合并进 `openspec/specs/`
- 这次改动挪到 `openspec/changes/archive/日期-名称/`

下次加功能再从「探索 / 出方案」开始。

---

## 对照一张表

| 你想做的事 | 跟 AI 说 |
|---|---|
| 还没想清楚 | `帮我探索一下……` / `/openspec-explore` |
| 已经想清楚 | `Propose a change to …` / `/openspec-propose` |
| 方案不对 | 直接说要改什么，或手改 md |
| 方案 OK，开工 | `Apply the xxx change.` / `/openspec-apply-change` |
| 做完了 | `Archive the xxx change.` / `/openspec-archive-change` |

---

## 给本项目的一个完整小例子

假设要加「答题历史分享」：

1. `openspec init`（若还没做过）
2. 聊天：`帮我探索如何在现有历史页上加分享功能`
3. 聊清楚后：`Propose the change we just discussed`
4. 打开 `openspec/changes/.../` 检查 `proposal.md`、`specs/`、`tasks.md`
5. 新对话：`Apply the ... change`
6. 测通后：`Archive the ... change`

---

## 三个避坑提醒

1. **先审方案再写代码** — 这是 OpenSpec 的全部意义。
2. **写代码前尽量新开对话** — 上下文干净，实现更稳。
3. **一次只做一个小功能** — 例如「错题本列表」先做，别一次塞「列表 + 复习 + 分享 + 导出」。

---

## 官方文档（需要时再看）

- 快速开始：https://openspec.dev/docs/quickstart
- 安装：https://openspec.dev/docs/installation
- 项目初始化：https://openspec.dev/docs/setup
