# review 工具箱改动

`dbm-reviewer` skill 负责通用缺陷与安全面，并定义 P0–P3 格式。本篇只查提单页这一侧的领域正确性。
**单据纵线（枚举、details 类型、提交体、回填、详情组件）走 `dbm-ticket-developer` 的 `references/review.md`**，
新增单据时几篇都要跑，合并成一份报告。

**检查项本身在 [checklist.md](checklist.md)**，本篇只给 diff 驱动的查法：命令、存量例外、定级。
先 `git diff --stat HEAD` 定位改动落点，只查命中的组。

| 改动落点 | 查哪组 |
| --- | --- |
| 新增 `{TICKET_TYPE}/`（业务工具箱，不是 `createApplyRoute` 申请页） | 全部 |
| 改已有提单页 | 一、二 |
| 改 `common/toolbox-field/` | 三 |
| 改 `dba-manage/`、`createDbaToolboxRoute`、非单据入口 | [dba-and-non-ticket.md](dba-and-non-ticket.md)：DBA 的 route `name` 必须是 `DBA_${ticketType}`，与枚举值不一致是约定 |
| 改 `com-factory/{db}/`、`details/{db}/` 类型 | 不是本篇，转 `dbm-ticket-developer` |

## 一、页面骨架

按 checklist 的「工具箱这两件」「页面骨架」两段核，其中三条有命令或存量例外：

- 提单页**不应该**出现 `defineOptions`：`rg -n 'defineOptions' src/views/db-manage/*/[A-Z]*/Index.vue`。
  **已知 3 处存量例外**：`MYSQL_DTS_DATA_MIGRATE`、`MYSQL_DTS_DATA_MIGRATE_RENAME`、
  `MONGODB_INSTANCE_FIX_STATUS`，只报本次新增的
- 新建页面用 `DbForm`。**存量大量 `BkForm` 不算问题，不要求改**
- `routerBack` 指向的路由名在该 DB 真实存在（见 [db-profiles.md](db-profiles.md)，已知 `SQLSERVER_ROLLBACK`
  两处指向不存在的路由名，属存量）

## 二、数据层与校验

按 checklist 的「模式」「表格与列」「批量操作」「提交时序」四段核。三条查法上的提醒：

- `EditableColumn` 内只有 `Editable` 系列组件——**只能读代码判断**，全仓库现在零违规，写不出会命中的搜索命令，
  但正因为干净，新引入的第一处就该拦下。命中即 **P1**
- 加载回调里的 `validate()` 分两种：查询**未命中**后触发报「不存在」是正确的，各 DB `cluster-column` 都这么写；
  查询命中后、或加载完下拉选项后触发是错的，会把用户还没录入的必填列立刻标红
- `validate()` 返回值没被当布尔判断——与 known-issues 的 `validate-failure-contract` 重合，那边命中即修

## 三、公共列组件

`rg -ln '<组件目录名>' src/views/db-manage` 列出全部调用方。查：是否逐个读过（抽样了就说「抽查 N 处」）；
有没有删掉说不清用途的条件分支；改动是加性的还是删了既有守卫。跨 DB 公共列的改动要在报告里列出影响范围。

## 定级

- **P0**：提单页缺失、业务工具箱路由 `name` 与枚举值不一致（懒加载运行时才失败）。DBA 页 `name` 是 `DBA_` 前缀，对不上枚举值不算 P0
- **P1**：`EditableColumn` 内混用普通表单组件、模式用 `v-if` 堆列、行工厂字段缺默认值
- **P2**：`tableKey` 漏刷、批量录入配置不全、`routerBack` 指向不存在的路由名
- **P3**：命名不跟随同 DB 存量（能被 eslint 拦的不必单列）
