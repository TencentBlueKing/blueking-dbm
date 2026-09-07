# 任务流节点操作入口重复实现

状态：未处理

## 现象

任务流详情页里「重试 / 跳过 / 强制失败 / 确认继续」这四个节点操作，各自有 3~4 个互相独立的入口实现：画布节点上的气泡、
节点详情面板的按钮、搜索树的批量操作、以及专家模式下画布的强制操作。四套实现调的是同一批接口，但确认弹层的载体
（自绘 div + tippy / `BkPopConfirm` / `InfoBox`）、标题、说明文案、确认按钮文案全部各写一遍，已经漂移。

后果不是「不优雅」，而是文案已经出现实际错误和自相矛盾，用户能直接看到：

- 节点详情的「重试」确认框，标题问的是重试，确认按钮却写着「确认继续」（`node-detail/Index.vue:67`）
- 同一个「跳过后节点会变成什么」的说明，在四个位置有四种写法，其中两处对状态的描述互相冲突：画布气泡说标记为
  「失败手动跳过」，节点详情说标记为「执行成功(失败手动跳过)」
- 「(失败手动跳过)」的括号在半角与全角之间摇摆，导致本该复用的一句话拆成了两个 i18n key

改任何一处操作的交互或文案，都必须记得同步另外三处，而这四处分布在三个目录层级下，没有任何交叉引用能提示它们相关。

## 证据

### 同一接口的独立调用点

| 接口 | 画布气泡 | 节点详情 | 画布强制操作（专家模式） | 搜索树批量 |
| ------------------- | ------------------------------ | -------------------------- | ------------------------------- | ---------------------------------------- |
| `retryTaskflowNode` | `node-operation/Retry.vue:61` | `node-detail/Index.vue:282` | `flow-canvas/Index.vue:291-296` | `BatchOperation.vue:270`（`batchRetryNodes`） |
| `skipTaskflowNode` | `node-operation/Skip.vue:63` | `node-detail/Index.vue:289` | `flow-canvas/Index.vue:298-301` | `BatchOperation.vue:276`（`batchSkipTaskflowNode`） |
| `forceFailflowNode` | `node-operation/ForceFail.vue:61` | `node-detail/Index.vue:296` | 无 | `BatchOperation.vue:227`（`batchForceFailTaskflowNode`） |

四个入口的参数是同一组（`{ node_id, root_id }`），成功回调也是同一件事（`messageSuccess(t('操作成功'))` + 通知父组件刷新），
但各自重写：`Retry.vue:61-67`、`node-detail/Index.vue:282-287`、`BatchOperation.vue:213-219`。

### 重试：确认层的四种写法

| 入口 | 文件:行 | 载体 | 标题 | 确认按钮 |
| ---------------- | ------------------------------ | -------------------- | ---------------------- | ---------------- |
| 画布气泡 | `node-operation/Retry.vue:19,21,29` | tippy + 自绘 div | 确认重试当前失败节点？ | 确认重试 |
| 节点详情 | `node-detail/Index.vue:67-69` | `BkPopConfirm` w=288 | 确认重试当前失败节点？ | **确认继续** |
| 画布强制重试 | `flow-canvas/Index.vue:291-296` | `InfoBox` + `BkAlert` | 确认强制重试该节点？ | 确认强制重试 |
| 搜索树批量重试 | `BatchOperation.vue:64` | `BkPopConfirm` | — | 批量重试 |

第二行的「确认继续」与标题不符，是从相邻的「确认继续执行当前待继续节点？」块（`node-detail/Index.vue:110-112`）复制后
漏改留下的。

### 跳过：同一语义的四种文案

- `normalNode.ts:753`：画布节点角标 `error_ignorable ? t('失败自动跳过') : t('失败手动跳过')`
- `node-detail/Index.vue:52`：状态区同一套三元判断，与上一条重复实现
- `node-operation/Skip.vue:22` 与 `node-detail/Index.vue:84`：「…当前节点标记为“执行成功(失败手动跳过)”」（半角括号）
- `flow-canvas/Index.vue:300` 与 `BatchOperation.vue:278`：「…当前节点将标记为 失败手动跳过」（无引号、无「执行成功」前缀）
- `BatchOperation.vue:83`：「…将被标记为“执行成功（失败手动跳过）”」（全角括号）

## 项目里已有的正确做法

同一个页面里的**状态**判定与配色刚做过一次收敛，可以直接照抄那个形状：
`detail/utils/nodeStatus.ts` 用 `getNodeDisplayStatus()` 收口判定、`NODE_STATUS_META` 收口文案与颜色，画布、搜索树、
节点详情、执行日志四处都从这一份取值。收敛前状态判定散在 8 处且已漂移，症状与本篇完全同类。

它没覆盖到的正是本篇：状态的**展示**统一了，状态的**操作**没有。`NODE_STATUS_META` 里只有 `text` 和配色，
没有「这个状态可以做哪些操作、每个操作的确认文案是什么」。

## 建议方向（未采纳）

把每个操作的确认层元数据（标题、说明、确认按钮文案、按钮主题、接口）收进一张表，四个入口都从表里取；
确认层的载体统一到 `BkPopConfirm`，只有专家模式的强制操作保留 `InfoBox`（它要额外挂风险 `BkAlert`，形态确实不同）。

不推荐的两条路，以及原因：

- **直接把四个入口合并成一个组件**。它们的触发时机和定位方式差别是真实的：画布气泡要按节点在 canvas 上的坐标算偏移
  （`flow-canvas/Index.vue:217-240` 每种操作一套 x 偏移量），批量操作面对的是节点数组而非单节点，接口都是另一套
  `batch*`。合并会把这些差异塞进条件分支，比现在更难改。只统一「确认层元数据 + 请求与回调」这一层就够。
- **只统一文案、保留四套确认组件**。文案抽成常量后，四处仍要各自决定用哪个 key，漏改的概率没有变化——
  `node-detail/Index.vue:67` 那个错误恰好就是「文案已经是 `t()` 调用了」的情况下发生的。

## 待查证

- 本篇只覆盖 `views/task-history/detail/**`。`views/ticket-center/**` 的单据详情里也有节点重试入口，是否是第五套
  实现、文案是否又一种写法，没有读过
- `batchRetryNodes` / `batchSkipTaskflowNode` 与单节点接口的语义差异（是否只是参数从 `node_id` 变 `node_ids`）
  没有读 `services/source/taskflow.ts` 核实，上表只核实了调用点
- 「确认继续」这处文案错误是否已有对应的缺陷单，未查
