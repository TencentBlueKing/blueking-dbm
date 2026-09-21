---
name: dbm-toolbox-developer
description: >-
  场景专属技能：DBM 工具箱模块的开发、迭代与 review。覆盖 mysql / tendb-cluster / redis / sqlserver /
  mongodb / oracle 六个 DB 的业务工具箱提单页（src/views/db-manage/{db}/{TICKET_TYPE}/Index.vue）、
  DBA 工具箱（dba-manage / createDbaToolboxRoute）、非单据入口（Webconsole、记录页、分析页）、
  页面模式、EditableTable 与列组件、工具箱路由与菜单。
  新增或修改工具箱提单页、改工具箱公共列组件、审查工具箱相关改动时使用；
  当用户询问提单页骨架、createToolboxRoute、createDbaToolboxRoute、EditableTable 数据层、
  批量录入、Webconsole 时也使用。服务申请页（createApplyRoute / *_APPLY）不在这里。
  单据本身的登记、details 类型、提交回填契约与单据详情组件在 dbm-ticket-developer skill。
---

# DBM 工具箱开发

本 skill 只写工具箱特有的约定：提单页怎么搭、路由与菜单怎么挂。**单据本身（`TicketTypes` 登记、details 类型、
提交与回填 hook、详情组件）归 `dbm-ticket-developer`**，其余 skill 分工见 `AGENTS.md`「技能索引」。

## 适用边界

**只有 6 个 DB 有工具箱**：`mysql`、`tendb-cluster`、`redis`、`mongodb`、`sqlserver`、`oracle`，判据是存在
`toolbox/toolboxMenuList.ts` 且有 `createToolboxRoute` 调用。大数据与 K8s 类 DB 没有工具箱是业务设定，
所以 `createToolboxRoute` 只映射 `TENDBCLUSTER` 一个目录例外是正确的，不要照 `createApplyRoute` 给它补
`ES` / `K8S_*` 映射。

**同目录形态不等于工具箱**：`{db}/{TICKET_TYPE}/Index.vue` 也被服务申请页占用，那 9 个 `*_APPLY` 走
`createApplyRoute`，归 `dbm-db-developer`；名字带 `APPLY` 但用 `createToolboxRoute` 注册的
（如 `TENDBCLUSTER_SPIDER_MNT_APPLY`）才是工具箱单据。四类入口的完整判定表、DBA 工具箱、
Webconsole / 记录页 / 分析页见 [dba-and-non-ticket.md](references/dba-and-non-ticket.md)。

## 在做什么

| 场景 | 读哪篇 |
| --- | --- |
| 新增单据 | [workflow-new.md](references/workflow-new.md) |
| **写完自检 / 核对完整性** | [checklist.md](references/checklist.md) |
| review 工具箱改动 | [workflow-review.md](references/workflow-review.md) |
| 选页面模式 / 抄模板 | [page-patterns.md](references/page-patterns.md) |
| 写表格数据层、批量操作、校验 | [editable-table.md](references/editable-table.md) |
| 选列组件或新建列 | [column-components.md](references/column-components.md) |
| 查某个 DB 的路径与差异 | [db-profiles.md](references/db-profiles.md) |
| 找 MySQL 同类单据 | [inventory-mysql.md](references/inventory-mysql.md) |
| DBA 工具箱 / Webconsole / 记录页 | [dba-and-non-ticket.md](references/dba-and-non-ticket.md) |

## 五件套

一个工具箱功能 = `dbm-ticket-developer` 的单据四件套（枚举、details 类型、提单入口、详情组件）+ 工具箱这两件。
缺任何一件功能在界面上就是断的。

| 产物 | 位置 |
| --- | --- |
| 提单页 | `src/views/db-manage/{db}/{TICKET_TYPE}/Index.vue`，目录名全大写 |
| 路由 + 菜单 | `{db}/routes.ts`、`{db}/toolbox/toolboxMenuList.ts` |

四件套各自的位置要求、导出链与命名对照见 `dbm-ticket-developer` 的 `references/registry.md`。
DBA 单据的提单页在 `{db}/dba-manage/{TICKET_TYPE}/`，菜单在 `dba-manage/Index.vue`，不是上面那条路径。

**四者必须完全一致**：`TicketTypes` 枚举值、提单目录名、路由 `name`、详情组件 `defineOptions({ name })`。
这条只约束业务工具箱，DBA 的 route `name` 是 `DBA_${枚举值}`，对不上枚举值是约定。
没有编译期保障，对不上时两种表现：目录名与枚举不一致，路由懒加载在**运行时**才失败；详情组件 `name`
不一致，com-factory 静默退回 `Default.vue`，页面能开但内容不对。

各 DB 的目录名有陷阱（`tendb-cluster` 在 views 下是短横线，在 details 和 com-factory 下是 `tendbCluster`），
见 [db-profiles.md](references/db-profiles.md)。

**菜单项**：单据入口 `id` 用 `TicketTypes`（与路由 `name` 一致），配 `dbConsoleValue`。`desc` 一句话说明只在
mysql / tendb-cluster 的存量菜单里有——这两个 DB 的新项要写，其余四个跟随同文件存量，不要为了对齐清单硬加。
一个入口绑多个单据类型时用 `bind: [TypeA, TypeB]`。菜单里还有非单据入口，`id` 是手写路由 name，见
[dba-and-non-ticket.md](references/dba-and-non-ticket.md)。

**一个 ticket_type 一套五件套。** 需求里出现多种「方式 / 模式」时先确认后端是否分配了独立 `ticket_type`：是就各自
独立建页，严禁合并成一个页面切换（跨页切换的正确做法是模式 F，见 [page-patterns.md](references/page-patterns.md)）。

工具箱单据的「再次提单」**不用登记路由**——`createToolboxRoute` 把路由 `name` 设成了枚举值，
`TicketClone.vue` 的映射会自动收录。DBA 页与非工具箱入口的规则见 `dbm-ticket-developer` 的
`references/registry.md`。

### createToolboxRoute

```ts
const { createRouteItem } = createToolboxRoute(DBTypes.MYSQL);
createRouteItem(TicketTypes.MYSQL_DATA_MIGRATE, t('数据迁移'));
createRouteItem(TicketTypes.MYSQL_RENAME_DATABASE, t('DB 重命名'), { dbConsole: 'mysql.toolbox.dbRename' });
createRouteItem(TicketTypes.MYSQL_IMPORT_SQLFILE, t('变更SQL执行'), {}, { params: '/:step?' });
```

按 `TicketTypes` 懒加载 `{db}/{TICKET_TYPE}/Index.vue`，自动把 `name`、`path`、`meta.ticketType` 设为枚举值
（前两项不在第三个参数的类型里，写不进去），`meta.fullscreen` 默认 `true`（`hideTitle` 只对 mysql 和
tendbcluster 自动为 `true`）。**这些都不要手写重复。** 第三个参数现存调用几乎只用来传 `dbConsole` 功能开关，
动态路径参数走第四个参数。

## 提单页要点

完整 template 与间距见 [page-patterns.md](references/page-patterns.md)。四条容易写错的：

- **表单容器用 `DbForm`，不是 `BkForm`。** 它比 `BkForm` 多做三件提单页需要的事：`watch(model, deep)` 置
  `window.changeConfirm`，有未提交内容时离开页面弹确认；`validate()` 失败滚动到第一个报错项；失败继续 `reject`。
  存量有大量 `BkForm`，**不要顺手改**
- **提单页不写 `defineOptions({ name })`**：路由 `name` 已由 `createToolboxRoute` 设为枚举值。六个 DB 的
  `createRouteItem` 共 140 条，其中只有 3 个 Index 写了 `defineOptions`，是例外不是范例。详情页相反，那里
  `name` 是硬约束。同目录形态另有 9 个服务申请页，不要算进工具箱提单数
- `defineExpose({ routerBack })` 指回该 DB 的工具箱首页，**路由名六个 DB 各不相同**，查
  [db-profiles.md](references/db-profiles.md)
- `SmartAction`、`DbForm`、`Editable*` 系列、`OperationColumn`、`DbResetButton`、`TicketInfoTable` 全局已注册
  （`src/common/importComps.ts`），不要 import

## 提交与回填

`useCreateTicket` / `useTicketDetail` 的完整契约（泛型必须是内联提交类型、`isToolbox` 分流、重复单据、
返回值语义、回填完整度、`clusters` / `specs` 兜底、提交体字段映射）在 `dbm-ticket-developer` 的
`references/submit-and-backfill.md`，**写提单页前先读那篇**。这里只列工具箱页面特有的四条：

- 入参形状 `{ details: {...}, ...formData.payload }`；提交前先 `await formRef.value!.validate()` 再
  `tableRef.value!.validate()`
- 工具箱页用 `useCreateTicket` 的默认 `isToolbox: true`，**不要显式传 `false`**，否则失败时错误条不会内联展示
- **`useTicketDetail` 不能漏**：`onSuccess` 里用 `createTicketPayload(ticketDetail)` 回填备注，行数据一律走行工厂
  组装，组装完刷 `tableKey`
- 表格特有的回填踩坑（域名解析时机、联动清空防误清、对象数组边界转换、资源标签竞态）见
  [editable-table.md](references/editable-table.md)

## 改动的联动面

新增或修改一个提单字段 = **四处同改**，缺一处就是 bug：提单页的列 → `details` 类型 → `useTicketDetail` 回填 →
详情页展示列。后三处归 `dbm-ticket-developer`。这一列若参与批量录入，还要第五处：`batchInputConfig`。

改后端字段名时三处使用点一起搜：

```bash
rg -n '<旧字段名>' src/services/model/ticket/details src/views/db-manage/<db>/<TICKET_TYPE> \
  src/views/ticket-center/common/ticket-detail/components/task-info/com-factory/<db>
```

给已有页面加一种模式时，先判断是不是独立 `ticket_type`：是就是新建一套五件套，否则按
[page-patterns.md](references/page-patterns.md) 拆模式子组件——现有页面若是 `v-if` 堆列实现的，加第三种模式之前
先把已有的拆出去。

改 `common/toolbox-field/` 下的公共列按 `AGENTS.md` 的公共代码规则走，先 `rg -ln` 列全调用方。跨 DB 公共列
（`src/views/db-manage/common/toolbox-field/column/`）影响全部六个 DB。

## 四条决策口诀

1. **协议或可编辑列随模式变化 → 拆模式子组件，页面零 `v-if` 分支**（[page-patterns.md](references/page-patterns.md)）
2. **`EditableColumn` 内只放 `Editable` 系列组件**，普通表单组件会让编辑态、校验联动、禁用态全部失效
3. **校验交给提交时机**，数据加载回调里只有「查询未命中、要报不存在」这一种情况可以手动 `validate()`
4. **列组件不感知页面业务**，差异化通过 props 注入；先找公共列，再找 DB 专属列，都没有才建页面私有列
