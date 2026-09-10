# 任务流节点操作有四个独立入口，改一处要看其它三处

- **命中**：改 `src/views/task-history/detail/**` 下重试 / 跳过 / 强制失败 / 确认继续的确认文案、按钮文案或交互。
  定位入口：`rg -ln 'retryTaskflowNode|skipTaskflowNode|forceFailflowNode|batchRetryNodes' src/views`
- **为什么**：四个入口调的是同一批接口，但确认弹层的载体（自绘 div + tippy / `BkPopConfirm` /
  `InfoBox`）、标题、说明、确认按钮文案全部各写一遍，漂移过一次已经漏到用户面前
- **改成**：改动一并在其它三处检查同样文案，有就报告。**统一确认层的方案未定**
- **不要**把四个入口合并成一个组件：它们的定位方式（画布气泡要按节点在 canvas 上的坐标算偏移）和接口（单节点
  vs `batch*`）差异是真实的，合并只会把差异塞进条件分支。也**不要**只统一文案、保留四套确认组件——文案抽成常量后，四处仍要各自决定用哪个
  key，漏改概率没变（历史上那个「标题问重试、按钮写确认继续」的错误，恰好就发生在文案已经是 `t()` 调用的情况下）
- **存量**：四个入口，全部在 `src/views/task-history/detail/components/task-flow/components/` 下：

  | 入口 | 文件 | 确认层 | 接口 |
  | --- | --- | --- | --- |
  | 画布节点气泡 | `flow-canvas/components/node-operation/Index.vue` | 自绘 | `retryTaskflowNode` / `skipTaskflowNode` / `forceFailflowNode` |
  | 节点详情面板 | `node-detail/Index.vue` | `BkPopConfirm` | 同上三个 |
  | 画布强制操作 | `flow-canvas/Index.vue` | `InfoBox` | `retryTaskflowNode` / `skipTaskflowNode` |
  | 搜索树批量 | `search-tree/components/BatchOperation.vue` | `InfoBox` | `batchRetryNodes` / `batchSkipTaskflowNode` / `batchForceFailTaskflowNode` |

  单节点入口的参数是同一组（`{ node_id, root_id }`），成功回调也是同一件事（`messageSuccess` +
  通知父组件刷新），但各自重写。「失败手动跳过」的说明有多种写法，括号在半角与全角之间摇摆，导致本该复用的一句话拆成两个
  i18n key
- **核实**：2026-09-10

## 补充

同一页面的节点**状态**判定与配色做过一次收敛，可以照抄那个形状：`src/views/task-history/detail/utils/nodeStatus.ts`
用 `getNodeDisplayStatus()` 收口判定、`NODE_STATUS_META` 收口文案与颜色，画布 / 搜索树 / 节点详情 /
执行日志四处都从这一份取值。它没覆盖的正是本篇——状态的展示统一了，状态的**操作**没有。

`src/views/ticket-center/**` 的单据详情里也有节点重试入口，是否是第五套实现未确认。

历史：commit `1f4597bea`（优化任务详情交互 #20324）把画布气泡原先的 `Retry.vue` / `Skip.vue` /
`ForceFail.vue` 三个文件合并成了 `node-operation/Index.vue`，并修掉了节点详情面板里的重试文案错误。入口数没变，仍是四个。
