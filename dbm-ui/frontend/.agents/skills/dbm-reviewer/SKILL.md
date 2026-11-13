---
name: dbm-reviewer
description: >-
  DBM 前端（TypeScript + Vue 3）的代码审查。查逻辑 bug、功能完整性、改动的连带影响、安全、性能、交互一致性，
  给出缺陷优先的 P0-P3 报告。
  当用户要求代码审查、code review、review 一下这次改动、看看有没有安全问题、提交前检查时使用。
---

# dbm-reviewer

审查代码改动，输出缺陷优先的报告。审查阶段全程只读：不改代码、不 `git add`、不提交。

每次审查回答六个问题：有没有逻辑 bug、功能是否完整、会不会带来隐藏的连带 bug、安全、性能、交互是否一致。
六项各一份清单，见第 5 节。

本 skill 只管**怎么查、怎么报**。项目规范（编码约定、架构、设计、各模块的领域约定）在其它 skill，这里不重复，
只在第 2 节按改动路径指过去。

## 1. 取改动范围

仓库根是 `blueking-dbm`，前端在 `dbm-ui/frontend`，所有命令在 `dbm-ui/frontend` 下执行。

默认审本地**未提交改动**：

```bash
git status --porcelain .   # 改动清单
git diff -- .              # 工作区
git diff --staged -- .     # 暂存区
```

未跟踪文件（`??`）没有 diff，直接整文件读。

改动为空时直接告知，不要自行转去审查历史提交或分支 diff。用户明确指定了范围才换取法：

```bash
git diff <base>...HEAD -- .   # 用户指定对比分支
git show <sha> -- .           # 用户指定某次提交
```

## 2. 读上下文

先弄清这次改动要做什么：用户的说明、`openspec/changes/` 下对应的提案、commit message。都没有时按 diff 推断，
并在报告开头写明推断出的意图。不知道要做什么，就判断不了功能是否完整。

再读 `AGENTS.md`，并按改动路径加载项目规范（直接读文件，不要凭记忆）：

| 改动路径                                                                                                     | 读                                   |
| ------------------------------------------------------------------------------------------------------------ | ------------------------------------ |
| 任何 `.vue` / `.ts`（编码约定全清单）                                                                        | `.agents/skills/dbm-frontend-developer/references/code-conventions.md` |
| 新增文件、目录结构有调整                                                                                     | `.agents/skills/dbm-frontend-developer/references/architecture.md` |
| `src/views/db-manage/**`（业务工具箱 `{TICKET_TYPE}/` 与 `dba-manage` 除外，含 `createApplyRoute` 申请页）、`src/common/const/dbTypes.ts`、`clusterTypes.ts` | `.agents/skills/dbm-db-developer/references/review-checklist.md` |
| `src/services/**`                                                                                            | `.agents/skills/dbm-frontend-developer/references/architecture.md`「服务层」 |
| `src/views/ticket-center/**`、`src/common/const/ticketTypes.ts`、`src/services/model/ticket/**`、`com-factory` 单据详情、`useCreateTicket` / `useTicketDetail` 调用 | `.agents/skills/dbm-ticket-developer/references/review.md` |
| `{TICKET_TYPE}/Index.vue`（`createApplyRoute` 申请页除外）、`createToolboxRoute`、`createDbaToolboxRoute`、`toolboxMenuList.ts`、`dba-manage/**`、`common/toolbox-field/**` | `.agents/skills/dbm-toolbox-developer/references/workflow-review.md` |
| `src/views/task-history/detail/**`                                                                           | `.agents/skills/dbm-reviewer/references/task-history-detail.md` |
| `src/layout/**`、`src/router/**`，或新增页面挂菜单入口                                                       | `.agents/skills/dbm-frontend-developer/references/navigation-menu.md` |
| URL 带 `?open=` 的直达链接入口                                                                               | `.agents/skills/dbm-frontend-developer/references/direct-link.md` |
| 同时有 `DbQuickSearch` 搜索栏和表格列筛选的列表页                                                            | `.agents/skills/dbm-frontend-developer/references/search-filter-sync.md` |
| 页面样式、布局、交互反馈、组件选型                                                                           | `.agents/skills/dbm-designer` |
| 新增或改 `TableColumn` 的 `width` / `min-width`                                                              | `.agents/skills/dbm-designer/list-page.md`「列宽约定」 |

判断与版本、配置有关的写法前，先看 `package.json` 与 `tsconfig.json`（Vue 小版本、`noUncheckedIndexedAccess`
是否开启）。它们决定的是「该不该报」：同一种写法在不同版本、不同配置下结论相反。

diff 看不出影响时，读被改函数的调用方、被改组件的父组件。

## 3. 跑 eslint 收集客观问题

只对改动文件跑，**不加 `--fix`**（审查阶段不改文件）：

```bash
npx eslint <改动的 .ts/.tsx/.vue 文件>
```

改了 `.less` 再跑 `npx stylelint <改动的 .less 文件>`。

不跑 `yarn type-check`（全量太慢），类型问题按 [references/logic.md](references/logic.md)「类型」人工看。

`src/` 没有单测基建：不要以「缺少测试」立 issue，不要建议新建测试文件或引入测试框架。

## 4. 缺陷门槛

同时满足才写进报告：

- 影响正确性、安全、性能或可维护性；
- 具体、可执行，能指到 `文件:行`；
- 由本次改动引入；
- 能从代码论证出触发场景；
- 作者知道后大概率会改。

不报：存量问题、猜测性担忧、有意的行为变更、不影响阅读的风格 nit、eslint / prettier 会自动修的格式问题。

### 立项前必须核对的三件事

以下三类是历史上误报、错定级最多的来源，写进报告前逐条核：

- **校验会不会拦住**：写「直接提交会带上空值 / 0」之前，先查对应列或表单项有没有必填 `rules`
  （`SpecColumn`、各 `target-capacity-column`、`ResourceTagColumn` 都有）。被校验拦住的只是「要重选」，不是「提交错数据」，最高 P2
- **入口有没有门控**：判断「数据未返回时会崩」之前，先看渲染入口是否已被 `v-if` / 计算属性挡住
  （如告警订阅 Tab 由 `isAbleSubscribe` 控制、批量入口由 `isClusterTypeAlarmSupported` 控制）。挡住了就降级或不报
- **接口语义以后端为准**：判断「会重复创建 / 字段被忽略 / 排序失效」之前，到 `dbm-ui/backend` 读对应 view
  （如 `db_package/views.py` 的 `bulk_create` 是 `update_or_create`；DRF `OrderingFilter` 对未知字段静默忽略，不会报错）

另外：「改了 A 字段同时重置 B 字段」「再次提单不回填依赖实时拓扑的方案」这类可能是有意设计，先找注释或同类页面的做法，
确实拿不准就放进「待人工验证」或直接问，不要定成 P1。

## 5. 六项检查

前三项每次都查，后三项按改动内容查。通用 review 常识不赘述，清单里只放容易漏、容易误报的点。

| 要回答的问题                     | 读                                                         | 什么时候读 |
| -------------------------------- | ---------------------------------------------------------- | ---------- |
| 有没有逻辑 bug                   | [references/logic.md](references/logic.md)                 | 每次 |
| 功能是否完整                     | [references/completeness.md](references/completeness.md)   | 每次 |
| 会不会带来隐藏的连带 bug         | [references/impact.md](references/impact.md)               | 每次 |
| 安全                             | [references/security.md](references/security.md)           | 渲染 HTML、跳转、本地存储、上传下载、权限、新增依赖 |
| 性能                             | [references/performance.md](references/performance.md)     | 列表 / 表格渲染、监听器、大数据量、路由或重型组件引入 |
| 交互是否一致                     | [references/interaction.md](references/interaction.md)     | 模板、样式、弹层、提示、表单 |

连带影响不在 diff 里：必须按 `impact.md` 走出 diff 读引用点，只读 diff 得不出「没有连带影响」的结论。

## 6. 输出

结论先行：一句话说清「有几个问题、最严重的是什么」，再按严重度排序列条目。改动意图是按 diff 推断的，写在结论之前。

每条一个条目：

```
[P1] 动词开头的问题标题 — src/views/db-manage/mysql/xxx/Index.vue:120
```

标题后跟一段短说明：什么场景下触发、结果怎样错。引用行范围尽量小，且落在本次 diff 内；两类例外：
功能缺失指向应当补上的位置，连带影响指向引起它的改动行、受影响的引用点写在说明里。

级别：

- `P0` 阻塞发布或必然崩溃；
- `P1` 需要立刻修的缺陷；
- `P2` 应当修的一般缺陷；
- `P3` 影响小但值得修。

没有合格问题就写「无问题发现」，不要凑数。

条目之后补三段：

- **六项结论**：逻辑、功能完整性、连带影响、安全、性能、交互一致性各一句——有问题（指向上面的条目）、未发现问题、
  或本次改动未涉及。连带影响要写明查了哪些引用点、哪些没展开；
- **残余风险**：改动可能影响到、但 diff 里看不出的地方；
- **待人工验证**：写清「哪个页面 + 哪个操作 + 预期结果」，不要声称自己已验证过。

最后询问用户是否需要修复、修哪几条；用户确认后才动代码。
