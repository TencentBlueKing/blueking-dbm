# BlueKing DBM Frontend

蓝鲸 DBM（数据库管理系统）的前端，Vue 3 + TypeScript 单页应用。

## 工作目录与命令

仓库根是 `blueking-dbm`（monorepo），前端在 `dbm-ui/frontend`。**所有命令必须在 `dbm-ui/frontend` 下执行**，git
hooks 也是先 `cd dbm-ui/frontend` 再跑。

| 命令                          | 用途                                     |
| ----------------------------- | ---------------------------------------- |
| `yarn dev`                    | 开发服务，`127.0.0.1:8088`，`strictPort` |
| `yarn type-check`             | `vue-tsc --build` 全量类型校验           |
| `npx eslint <改动文件> --fix` | 校验改动文件，见下方说明                 |
| `yarn prettier`               | 格式化 `./src`                           |
| `yarn build`                  | 生产构建                                 |

`yarn lint` 是 `run-s lint:*`，覆盖范围有坑，不要当成全项目检查：`lint:oxlint` 只查 `correctness`，`lint:script`
的 eslint **只覆盖 `src/views/ticket-center/common/ticket-detail`**，`lint:lint-staged` 只处理已 `git add`
的文件。所以校验自己的改动要么直接 `npx eslint <改动文件> --fix`，要么 `git add` 后跑 `yarn lint:lint-staged`（它对
`.js/.ts/.tsx/.vue` 跑 eslint + prettier，对 `.less` 跑 stylelint）。

commit message 走 Conventional Commits，`commit-msg` 钩子会跑 commitlint 校验（type 白名单见 `commitlint.config.mjs`）。

## 改完怎么验证

`src/` 下没有单元测试，也没有单测基建。**不要为了"有测试"而新建测试文件或引入测试框架。**

**验证命令（type-check、eslint、stylelint 等）执行前先经用户确认，不要改完代码就自动跑。** 用户同意后按默认顺序执行：

1. `yarn type-check` 通过
2. 改动文件 `npx eslint <改动文件> --fix` 通过，改了样式再补 stylelint
3. 需要运行时验证的，写清「哪个页面 + 哪个操作 + 预期结果」交给人确认，不要声称自己已经验证过

## 仓库分层

`src/` 源码，`public/` 静态资源（构建后原样输出），`lib/` 内部库（别名 `@lib/*`），`openspec/`
变更提案与规格（未纳入 git）。

**`src/` 各目录职责、组件命名、页面怎么拆**见 `dbm-frontend-developer` 的 `references/architecture.md`。

## 项目独有约定

只列工具查不出来的。导入顺序、模板属性顺序、缩进格式由 ESLint / Prettier / Stylelint 强制，写错跑一次 `--fix`
就会自动修，不必手工记忆。

下面六条是写每一行代码都会用到的，漏了直接产出错误代码，所以常驻此处：

- **vue / vue-router 的 API 已 auto-import**：`ref`、`computed`、`watch`、`useRouter`、`useRoute` 等不要显式 import
- 文案一律走 `t()`（`useI18n`），语言包在 `src/locales/`
- 不用 `any`，用具体类型或 `unknown`
- 路径别名优先于相对路径（`@services/*`、`@components/*`、`@views/*` 等），完整清单见 `tsconfig.json`
- 新建 `.vue` / `.ts` 文件要带 MIT 版权头，照抄同目录已有文件的头部
- 类名写完整的嵌套类名，禁止 `&_name`、`&-name`、`--name`

**完整清单**（script setup 宏顺序、Props / Emits 写法、组件选型优先级、Pinia 风格、缩进等）见
`dbm-frontend-developer` 的 `references/code-conventions.md`，**改 `src/` 下任何文件前读**。

## 工作方式

编码前：

- 明确假设，不确定时询问而非猜测；存在歧义时列出多种解释，不默默选定一种
- 有明显更简单的做法，直接指出
- 发现代码矛盾、逻辑不一致时暂停，请求澄清
- 重构 / 优化类需求，先理解现有功能，给出方案请求确认

改动范围：

- 只改与当前任务直接相关的代码，严格匹配现有代码风格
- 精简和重写只针对本次任务已经动到的代码；不顺手优化相邻代码、注释、排版
- 不重构原本能正常运行的模块
- 本次修改产生的无效导入、废弃变量直接删除
- 项目原有的死代码、冗余内容只做文字提醒，不擅自删除

改被多处引用的公共代码（`components/`、`hooks/`、`services/`）：

- 按引用点逐个读，不用命名模式抽样；确实抽样了就写「抽查 N 处」，不说成「已确认全部调用方」
- 删除看不懂的条件分支前，先能复述它区分了什么；说不清就不删
- 一个入口承担多种调用意图时，先枚举意图再定判据，不用「多数场景对」的默认值覆盖少数场景
- 优先加性方案（加判据、加 API），而不是删既有守卫
- 需求与代码现状冲突时不自行选边：先弄清现有实现在区分什么，能同时满足就给兼容判据，不能就摆出来问

实现取舍：

- 用最少的代码解决问题
- 不为一次性需求创建抽象层，不为"未来可能用到"增加扩展性和可配置性
- 不抽离没有复用性的代码，允许大段代码保持阅读的完整性
- 必要的代码注释，变量注释，方法功能注释，逻辑分支注释

多步骤任务先给简短执行计划，并标注每一步的验证方式。

已知问题：**改 `src/` 下任何文件前、以及用户指出写法问题时，按 `known-issues` skill 执行**，边界与写入规范都在
`.agents/skills/known-issues/SKILL.md`，此处不重复。**扫完必须在回复里写一行 `known-issues: 已扫，命中 N 条`**，N
为 0 也要写——这是漏扫的唯一可观测信号，所以只能写在这里，写进 skill 就失效了。

## 技能索引

`.agents/skills/` 按各 `SKILL.md` 的 description 触发。DBM 前端相关的六个按职责划分，互不重叠：

| skill | 职责 | 什么时候读 |
| ------------------------ | ---------------- | ------------------------------------------------------------ |
| `dbm-frontend-developer` | 架构与代码逻辑   | **改 `src/` 下任何前端代码前**（编码约定全清单、src 分层）；改 `services/**` 或新增接口；改 `src/layout/**`、`src/router/**` 或新增页面要挂菜单入口；做 URL 带 `?open=` 的直达链接；页面同时有 `DbQuickSearch` 搜索栏和表格列筛选 |
| `dbm-designer`          | 设计             | 新建或修改页面、组件、样式前；查布局、留白、令牌、组件选型、视觉与交互反馈 |
| `dbm-db-developer`       | 场景：db 模块    | 接入新 DB、改 `db-manage/common/**` 或某个 DB 的集群列表 / 详情 / 实例列表、改 DB 类型登记前；判断需求是全部 DB / 一类 / 某一个时 |
| `dbm-ticket-developer`   | 场景：单据模块   | 新增或修改任何单据类型、改 `ticket-center/**` 或 `services/model/ticket/**` 前 |
| `dbm-toolbox-developer`  | 场景：工具箱模块 | 改 `db-manage/{db}/{TICKET_TYPE}/**`（申请页除外）、工具箱路由与菜单、`dba-manage` 前 |
| `dbm-reviewer`           | 审查             | 用户要求 code review、提交前检查时 |

边界判据：约定换个业务模块照样成立 → `dbm-frontend-developer`；只定「长什么样、怎么反馈」→
`dbm-designer`；只对某一个模块成立 → 对应的场景 skill；只管「怎么查、怎么报」→ `dbm-reviewer`。

此外 `known-issues` 存已固化的检查项，改 `src/` 下文件前必读（见上「工作方式」）。

## 不要碰

- `dist/`、`node_modules/`、`src/types/auto-imports.d.ts`（自动生成）
- `.env.local`、`.env.production`
- `auto-copyright.js`：会重写全仓库文件，且在 `"type": "module"` 下用 `require` 会直接报错，不要执行

<!-- CODEGRAPH_START -->
## CodeGraph

仓库已被 CodeGraph 索引（根目录存在 `.codegraph/`）时，需要理解或定位代码，优先用它，而不是先 grep / find 或直接读文件：

- **MCP 工具**（可用时）：`codegraph_explore` 一次调用就能回答大部分代码问题——相关符号的原始源码，以及它们之间的调用链路，包含 grep 追不到的动态分发跳转。查询里写上文件名或符号名，就能拿到它当前带行号的源码。如果工具已列出但处于延迟加载状态，按名字通过工具检索加载。
- **Shell**（始终可用）：`codegraph explore "<符号名或问题>"` 输出同样的内容。

没有 `.codegraph/` 目录就完全跳过 CodeGraph——是否建索引由用户决定。
<!-- CODEGRAPH_END -->
