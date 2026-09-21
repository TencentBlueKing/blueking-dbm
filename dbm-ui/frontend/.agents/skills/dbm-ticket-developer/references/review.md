# review 单据改动

`dbm-reviewer` skill 负责通用缺陷与安全面，并定义 P0–P3 格式。本篇只查单据纵线，改动涉及单据时两篇都跑，
合并成一份报告。入口页骨架另查：工具箱走 `dbm-toolbox-developer` 的 `workflow-review.md`，集群管理面走
`dbm-db-developer` 的 `review-checklist.md`。

**检查项本身在 [checklist.md](checklist.md)**，本篇只给 diff 驱动的查法：命令、存量例外、定级。
review 新增单据时先按 checklist 过一遍完整性，再回来按下面查改动质量——**只查改动命中的组**。

| 改动落点 | 查哪组 |
| --- | --- |
| 新增一个 `ticket_type` | 全部 |
| 改 `details/` 类型 | 一、二、三、四 |
| 改提交体或 `useCreateTicket` 调用 | 二 |
| 改 `useTicketDetail` 回填 | 三 |
| 改 `com-factory/` | 四 |
| 改三个 hook 本身 | 五 |

## 一、四件套完整性

```bash
TYPE=MYSQL_YOUR_NEW_TYPE; NS=mysql
CF=src/views/ticket-center/common/ticket-detail/components/task-info/com-factory
rg -n "$TYPE" src/common/const/ticketTypes.ts                 # 枚举
rg -ln "$TYPE" src/views/db-manage src/views/service-apply    # 入口
rg -n "$TYPE" $CF/$NS                                         # 详情组件
```

任一条无输出即 **P0**。另查：

- **details 类型不能用枚举值搜**（文件名是驼峰，内容里不出现枚举字符串），查 `details/$NS/index.ts` 有没有对应的
  `export * from './xxx'`。这一环有编译期保障，`yarn type-check` 过了就不用手查
- 详情组件没在两处重复：`rg -o "name: TicketTypes\.([A-Z0-9_]+)" -r '$1' $CF | sort | uniq -d`
- 需求里每种独立 `ticket_type` 都有自己的一套，没被合并

## 二、提交侧

- **`useCreateTicket` 泛型不是详情类型**，本次新增的命中即 **P1**：

  ```bash
  rg -n 'useCreateTicket<(Mysql|Redis|Mongodb|Sqlserver|TendbCluster|Oracle|Doris|Kafka|Hdfs|Pulsar|Riak|Es)\.' src/views
  ```

  **已知存量 1 处**：`MYSQL_MIGRATE_SINGLE/Index.vue` 的 `Mysql.ResourcePool.MigrateSingle`
  （它 `extends ResourcePoolDetailBase extends DetailBase`）。不要重复报，也不要顺手改

- **非工具箱入口漏传 `isToolbox: false`**，本次新增的命中即 **P1**（失败时用户没有任何反馈）：

  ```bash
  for f in $(rg -l "useCreateTicket" src/views src/hooks | rg -v '/[A-Z][A-Z0-9_]*/' | rg -v "hooks/useCreateTicket|hooks/index"); do
    rg -A6 "useCreateTicket[<(]" "$f" | rg -q "isToolbox" || echo "漏传: $f"
  done
  ```

  **已知存量 7 处**（`common/machine-expansion`、`machine-expansion-es`、`machine-replace`、`machine-replace-es`、
  `machine-shrink`，`doris/common/upgrade-version`，`kafka/list/components/TopicRebalance.vue`）。
  只在改到这些文件时顺带修，不要全量清理

- `run` 的返回值被当异常处理（`try/catch` 期待它 throw）——它不会 reject，`catch` 块是死代码
- 提交体与协议一致
- 其余提交体检查项（字段名是否协议原名、资源标签双字段、radio 直绑枚举）过 checklist 的「提交」段

## 三、回填侧

- **回填完整度**：入口页每一列逐个对照 `useTicketDetail` 的 `onSuccess`。**必须手工逐项对照，没有替代命令。**
  漏项即 **P1**，高频漏点是资源标签和规格 `spec_id`
- `clusters` / `specs` 可选链兜底，**只查本次新增的行**（直接索引是存量多数写法，全量扫会淹掉本次改动）：

  ```bash
  git diff -U0 HEAD -- src | rg -n '^\+.*\.(clusters|specs)\['
  ```

  新增的命中即 **P0**，存量只提醒

- 新增的非工具箱单据要支持「再次提单」的，`TicketClone.vue` 的 `ticketTypeRouteNameMap` 有没有跟上。
  DBA 页 `name` 是 `DBA_${ticketType}`，默认再次提单落到同 ticket_type 的业务工具箱页，不要当成漏登记去改映射
- 用 props 把 `ticketDetails` 往子组件传，而不是子组件各自调 `useTicketDetail`——hook 有 1 秒缓存不会重复请求，
  传 props 反而让子组件与页面耦合

## 四、详情组件

逐条过 checklist 的「详情组件」段，本次新增的字段有没有对应列。另查一条 checklist 没有的：

- 新组件被放进 `com-factory/common/` 或 `components/`——这两个目录是给子组件用的，带 `TicketTypes` 名字的
  组件放进去会被工厂误收

## 五、改公共 hook

`useCreateTicket` 190 处调用、`useTicketDetail` 182 处，属于 `AGENTS.md` 说的公共代码，按那条规则走。额外注意：

- `isToolbox` 分支、重复单据 `8704005` 分支、`errors` 的字符串数组 / 行级数组两种形态，删任何一支之前要能复述
  它在区分什么
- 改返回值语义（现在是 `Promise<number | undefined>`，不 reject）就是改了全部调用方的错误处理契约，
  影响面必须穷举，不能抽样

## 定级

- **P0**：四件套缺件、详情组件 `name` 不匹配、新增的 `clusters` / `specs` 直接索引
- **P1**：回填漏项、`useCreateTicket` 用详情类型、非工具箱入口漏传 `isToolbox: false`、详情组件臆造字段名
- **P2**：`TicketClone` 路由映射漏登记、详情组件空值口径不统一、提交体字段名与协议有出入但不影响功能
- **P3**：详情组件形态选得不贴（能被 eslint 拦的不必单列）

**存量数据核实**：2026-09-21
