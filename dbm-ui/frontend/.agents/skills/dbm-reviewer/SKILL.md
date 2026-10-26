---
name: dbm-reviewer
description: >-
  DBM 前端的代码审查。查代码规范、逻辑正确性、交互一致性、安全与性能，给出缺陷优先的 P0-P3 报告。
  当用户要求代码审查、code review、review 一下这次改动、看看有没有安全问题、提交前检查时使用。
---

# dbm-reviewer

审查本地**未提交改动**，输出缺陷优先的报告。审查阶段全程只读：不改代码、不 `git add`、不提交。

本 skill 只管**怎么查、怎么报**：取 diff、缺陷门槛、跨模块的高频缺陷、P0–P3 输出格式。
判断「这么写对不对」所依据的规范本身不在这里——编码约定与架构在 `dbm-frontend-developer`（`AGENTS.md`
只留了六条常驻摘要），设计与交互反馈在 `dbm-designer`，各业务模块的领域约定在对应的场景 skill，
按第 2 节的表加载。

## 1. 取改动范围

仓库根是 `blueking-dbm`，前端在 `dbm-ui/frontend`，所有命令在 `dbm-ui/frontend` 下执行。

```bash
git status --porcelain .   # 改动清单
git diff -- .              # 工作区
git diff --staged -- .     # 暂存区
```

未跟踪文件（`??`）没有 diff，直接整文件读。

改动为空时直接告知，不要转而审查历史提交或分支 diff。

用户明确要求「扫一遍某个目录 / 整个 views」而不是审 diff 时，切到全量扫描模式，按
[references/full-scan.md](references/full-scan.md) 执行；第 4 节「由本次改动引入」那条门槛在该模式下不适用，其余照旧。

## 2. 读上下文

先读 `AGENTS.md`，再按改动路径加载规则（直接读文件，不要凭记忆）：

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

diff 看不出影响时，读被改函数的调用方、被改组件的父组件。

## 3. 跑 eslint 收集客观问题

只对改动文件跑，**不加 `--fix`**（审查阶段不改文件）：

```bash
npx eslint <改动的 .ts/.tsx/.vue 文件>
```

改了 `.less` 再跑 `npx stylelint <改动的 .less 文件>`。

不跑 `yarn type-check`（全量太慢），但要人工看类型问题：新增 `any`、用断言掩盖类型错误、接口字段与 `services`
模型不一致。

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

## 5. 检查清单

通用 review 常识不赘述，重点扫以下项目高频问题。编码约定（auto-import、script setup 宏顺序、Props / Emits 写法、
`any`、路径别名、Less 类名、版权头、`t()`）照 `dbm-frontend-developer` 的 `references/code-conventions.md`
逐条核，本篇不重复；各模块的领域约定在第 2 节表格指向的清单里，也不重复。

### Vue 3 响应式

- 解构 `reactive()` 对象导致失去响应（Vue 3.5 的 `defineProps()` 解构默认保持响应，不要报）；
- `setInterval` / `addEventListener` / 第三方实例未在 `onBeforeUnmount` 清理；`<script setup>` 里的
  `watch` / `watchEffect` 会随组件卸载自动 stop，不要报。普通 `setup()` 或把 stop handle 存到外部时才查是否漏停；
- `computed` 里发请求或改状态；
- 列表存在增删排序时 `v-for` 用 index 当 key；
- 无必要的 `{ deep: true }`，`watchEffect` 依赖失控。

### 前端安全

- XSS：`v-html` 的内容必须先过 `DOMPurify.sanitize()`（既有写法见 `src/components/system-version-log/Index.vue`），只加
  `<!-- eslint-disable vue/no-v-html -->` 绕过 lint 而不 sanitize 按 P0 / P1 报；
- 把接口字段或用户输入拼进 `el.innerHTML` 同样是注入点，新代码改用 `textContent` 或渲染函数；
- 「剥 HTML 标签取纯文本」也不能用 `div.innerHTML = html`：赋值瞬间 `<img onerror>` 就会执行。改用
  `new DOMParser().parseFromString(html, 'text/html').body.textContent`（DOMParser 生成的文档不执行脚本、不加载资源），
  命中按 P0 报；
- 出现 `eval`、`new Function`、`setTimeout('字符串')` 执行动态字符串；
- 跳转：`window.open` / `location.href` 的 url 来自接口或 query 参数时，要校验同源或白名单，防 `javascript:`
  伪协议与开放重定向；外链 `target="_blank"` 需带 `rel="noopener noreferrer"`；
- 敏感信息：密码、token、密钥不落 `localStorage` / `sessionStorage` / `document.cookie`（经 `src/common/cache.ts`
  存的同样要看存了什么），不 `console.log`，不作为 GET query 参数或出现在 url 里；
- 权限：前端隐藏按钮不等于有权限，下架 / 删除 / 重启 / 清档等破坏性操作必须依赖后端鉴权并有二次确认，不要新增只凭前端判断就发起的高危请求；
- 外部内容：上传前校验类型与大小，下载地址用后端返回值而非用户输入拼接，`iframe` 的 `src` 不接受用户输入；
- 新增第三方依赖要说明来源与必要性，不引入未审计的小众包。

### 数据与请求

- `services` 新接口缺类型，或类型与后端字段不符；
- 异步无错误处理，失败时 loading 不复位。手动维护的 `isLoading` 只在 `onSuccess` 里置 false 的，要补 `onError`；
  `try/finally` 里用 `.then` 而不 `await` 的，`finally` 会提前复位 loading，按钮可重复提交；
- 快速切换筛选 / 分页产生请求竞态，后到的旧响应覆盖新数据。修法用请求序号（`let seq`，`.then` 里比对），
  跨页全选、按域名反查集群这类「一次性」请求同样要比对；
- 分页、排序、搜索参数与请求不同步；**换筛选条件不把 `current` 置 1**，按旧 offset 请求出空列表；
- 复制全部 / 导出 / 跨页全选另起请求时，参数要和列表 `dataSource` 一致（如资源池的 `for_biz`），不能只展开搜索参数；
- 开新标签打开业务路由（`taskHistoryDetail`、`bizTicketManage` 等）且数据来自别的业务时，href 要过
  `getBusinessHref(href, row.bk_biz_id)`；`window.open` 的目标写成 `'__blank'` 是普通窗口名，不是新开标签。

### 空值与模板

- `arr?.[0].x`：数组是 `[]` 时 `[0]` 为 `undefined` 照样抛，要写 `arr?.[0]?.x`；`Object.values(obj)[0]!.x` 同理；
- `map[key].list`：`map` 异步填充（如 `useAlarmSubscribe` 的 `metricsMap`）时要写 `map[key]?.list`；
- `JSON.parse(decodeURIComponent(route.query[...]))` 没有 `try`：用 `@utils` 的 `parseQueryMemo`；
  `JSON.parse(localStorage...)` 同样要 `try` 并校验类型；
- `{{ value || '--' }}` 会把数字 0 显示成 `--`；
- `Array(n)` 的 n 来自除法时，要守住整数且大于 0，否则 `RangeError`；
- `<script setup>` 里拿 `computed` / `ref` 直接做 `if (hasXxx)` 判断，没写 `.value`，条件恒为真；
- 修饰符拼写（`v-model.tirm` 不会报错，只是不生效）；
- 整列共用一个 `isExpand` ref 的展开 / 收起，会让所有行一起展开，要按行 id 记；
- bkui-vue `Upload` 的 `beforeUpload` 只认严格的 `false`，`async` 函数里 `return;` 仍会上传。

### 表格列宽

新增或改了 `TableColumn` 的 `width` / `min-width` 时，逐条对照 `.agents/skills/dbm-designer/list-page.md`
「列宽约定」（工具箱 `EditableColumn` 不走这张表），known-issues 的 `table-column-width` 同主题。

### 单据提交与回填（跨模块高频）

细则在 `dbm-ticket-developer` 的 `references/review.md`，这里只列反复出现的几条：

- 不在工具箱页里调 `useCreateTicket`（集群列表弹窗、详情页操作等）必须传 `isToolbox: false`，否则失败只发
  `db-toolbox-error` 事件，页面没有任何提示；
- `useTicketDetail` 回填要覆盖页面上所有会提交的列。资源标签回填带上 `label_names`，写成
  `{ id, value }`；`clusters[id].immute_domain` 用可选链；
- 字符串拼接里混用三元：`a += cond ? '\n' : '' + b` 实际是 `a += cond ? '\n' : ('' + b)`，用 `map().join()` 代替；
- `TicketClone.vue` 映射的路由名必须真实注册，`router.resolve` 对未知 name 直接抛错；
- 详情工厂资源池目录与普通目录有同名组件时，按 `details.ip_source` 分流，新增同名组件要确认两份读的结构确实不同。

### 公共代码改动

- diff 删掉了条件分支、守卫或标志位：能否复述它原本区分什么，说不清就按 P1 报，不默认是历史残留；
- 改了 `components/`、`hooks/`、`services/` 的公共行为：影响面须按引用点穷举，抽样得出的「全部调用方都安全」不成立；
- 一个入口承担多种调用意图（如条件变更 / 原地刷新）时，新判据是否覆盖全部意图，而非只覆盖当前场景。

### task-history/detail 特有

改到 `src/views/task-history/detail/**` 时按
[references/task-history-detail.md](references/task-history-detail.md) 扫复发点。

## 6. 输出

结论先行：一句话说清「有几个问题、最严重的是什么」，再按严重度排序列条目。

每条一个条目：

```
[P1] 动词开头的问题标题 — src/views/db-manage/mysql/xxx/Index.vue:120
```

标题后跟一段短说明：什么场景下触发、结果怎样错。引用行范围尽量小，且必须落在本次 diff 内。

级别：

- `P0` 阻塞发布或必然崩溃；
- `P1` 需要立刻修的缺陷；
- `P2` 应当修的一般缺陷；
- `P3` 影响小但值得修。

没有合格问题就写「无问题发现」，不要凑数。

条目之后补两段：

- **残余风险**：改动可能影响到、但 diff 里看不出的地方；
- **待人工验证**：写清「哪个页面 + 哪个操作 + 预期结果」，不要声称自己已验证过。

最后询问用户是否需要修复、修哪几条；用户确认后才动代码。
