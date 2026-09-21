# 列表页范式

新建列表页按以下标准骨架实现，不要自创结构。

## 标准骨架

```
操作区（主按钮 → 批量操作 → 导出 → 搜索框居右）
  ↓ 16px
表格
  ↓
分页栏（60px，右对齐）
```

- 操作区 flex 横排，搜索框用 `margin-left: auto` 推到右侧，**不要用 `justify-content: space-between`**（左侧按钮数量不定）
- 按钮较多时允许 `flex-wrap: wrap; gap: 8px`

## 操作区

顺序固定：主按钮（实心主色）→ 批量操作 → 导出 / 复制 → 搜索（最右）。

按钮之间间距 8px。

搜索栏与表格列筛选是同一份条件，必须双向同步。见 `dbm-frontend-developer` 的 `references/search-filter-sync.md`。

## 搜索区宽度

| 宽度  | 场景                                 |
| ----- | ------------------------------------ |
| 500px | 集群列表、实例列表、白名单（主流）   |
| 550px | 单据中心                             |
| 560px | 标签管理、人员管理、资源池（条件多） |

## 列宽约定

取值以 `src/views/db-manage/common/cluster-table/`、`instance-table/` 的公共列为准。新列按语义就近取档，**不要新造中间值**。工具箱 `EditableColumn` 不走这张表。

允许的数字：`30 / 80 / 100 / 120 / 140 / 150 / 160 / 180 / 200 / 220 / 240 / 280`。

### 优先 `min-width`

新列默认写 `:min-width`，让有剩余宽度时跟着撑。`width` 只留给视觉上撑开就会变形的列：操作图标列 30、选择列 80。

同一张表、同一语义族必须统一用其中一种。不要主域名 `min-width: 180` 配从域名 `width: 280`。存量里大量 `width` 不要顺手改。

全屏列表与选择器弹窗（常见 `max-height: 472`）可用宽度不同，**不要跨容器强求同宽**。

已出现过的 `col-key` 先 `rg -A3 'col-key="<字段名>"' src`（或 `colKey: '<字段名>'`），取现有取值之一，不新造。不要按字段名建 `Record<field, number>`。

屏宽 `1366` 断点只给域名类（及实例地址）：`window.innerWidth < 1366 ? 窄档 : 宽档`。存量是 setup 期一次性求值，新列同样即可，不要扩散到非域名列。

### 语义档

| 语义 | 属性 | 取值 | 代表列 |
| --- | --- | --- | --- |
| 操作列（仅更多图标） | `width` | 30 | `cluster-table` / `instance-table` `OperationColumn` |
| 选择列 | `width` | 80 | 表头带全选下拉，撑开会变形 |
| ID | `min-width` | 80 | `IdColumn` |
| 状态、时区 | `min-width` | 100 | `StatusColumn`、`time_zone` |
| 管控区域 | `min-width` | 120 | `bk_cloud_id` |
| 人名、IP、短角色、园区、操作系统 | `min-width` | 140 | `creator`、`IpColumn`、实例表 `role` / `bk_sub_zone` / `bk_os_name` |
| 模块名、短状态文案、shard | `min-width` | 150 | `ModuleNameColumn`、`MongodbStateColumn`、`ShardColumn` |
| 部署时间 | `min-width` | 180 | 集群表 `create_at` |
| 标签 | `min-width` | 200 | `ClusterTagColumn` |
| 长版本号 | `min-width` | 240 | 实例表 `version` |
| 容量统计 | `min-width` | 280 | `ClusterStatsColumn` |
| 操作列（文字链接，≤3 个） | `min-width` | 80 或 140 | 单据 / 配置类，按按钮数量取档 |
| 别名、短名称、主版本、地域 | `min-width` | 150 | `ClusterAliasColumn`、`major_version`、`region` |
| 容灾要求 | `min-width` | 160 | `disaster_tolerance_level` |
| 名称类、角色节点 | `min-width` | 200 | 集群表 `ClusterNameColumn`、`RoleColumn` |
| 规格 | `min-width` | 220 | `cluster_spec` |
| 从域名 | `min-width` | 280 | `SlaveDomainColumn` |
| 主域名 / 实例域名 | `min-width` | 180 / 280 | 屏宽 `< 1366` 用 180，否则 280 |
| 实例地址 | `min-width` | 150 / 200 | 同上断点 |

对不上任何语义时取最近一档，不要发明 `90 / 110 / 175 / 190`。

## 操作列的两种流派

按操作数量选，不要混用：

- **超过 3 个操作** → 收进左侧 30px 的气泡菜单。菜单项 `line-height: 32px`、`padding: 0 12px`、字号 12px、hover 变 #3a84ff。
- **3 个及以内** → 右侧 inline 文字链接按钮，间距 8px。

## 分页与空态

| 项          | 值                                 |
| ----------- | ---------------------------------- |
| 默认每页    | 20                                 |
| 每页选项    | 10 / 20 / 50 / 100（可加 200/500） |
| 持久化      | 记住用户选择的每页条数             |
| 布局        | 总数 + 每页条数 + 页码，右对齐     |
| 分页栏高度  | 60px，左右 padding 16px            |
| 空态区高度  | 260px，padding-top 48px，字号 12px |

空态三态：异常 → 错误插图 + 刷新按钮；搜索无结果 → 提示 + 清空搜索入口；默认 → 空插图。

Loading：遮罩罩住表格区域，不遮整页。

## 行内渲染的 6 个套路

| 模式                | 规范                                                    |
| ------------------- | ------------------------------------------------------- |
| 复制按钮 hover 显形 | 默认隐藏，行 hover 时显示；色 #3a84ff，与文字间距 4px   |
| 多值折叠            | 只渲染前 6 条，超出显示「共 n 个 查看更多」             |
| 空值占位            | `--`                                                    |
| 搜索命中高亮        | #F59500（全局搜索结果页存量用 #FF9C01，新列表列不要跟） |
| 行状态着色          | 选中 #ebf2ff / 新增 #f3fcf5 / 离线字色 #c4c6cc          |
| 单行省略            | 溢出才挂 tooltip                                        |

## 批量选择

- 批量按钮禁用条件：未选中任何行；禁用时必须配 tooltip 说明原因
- 新请求（非翻页 / 排序触发）自动清空已选
- 支持按行禁用选择（返回禁用或提示文案）

## 列显示配置

- 列显隐配置持久化到**服务端用户偏好**，不是 localStorage
- 主键列必须锁死，不可隐藏
