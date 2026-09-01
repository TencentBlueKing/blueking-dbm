# 表格列宽在多处独立取值

状态：未处理

## 现象

同一语义的表格列（访问入口、集群名称、状态、管控区域…）在不同页面各写各的宽度，且 `width`（固定宽）与
`minWidth`（可伸缩）两种语义混用。混用比数字不一致影响更大：同一个域名列在一个弹窗里能撑开、在另一个里撑不开。

## 证据

### 1. cluster-selector 下 10 份按 DB 类型复制的选择器

`src/components/cluster-selector/components/*/Index.vue`，列是同一套，宽度各写各的：

| colKey          | 出现过的取值                    |
| --------------- | ------------------------------- |
| `master_domain` | 240 / 250 / 280 / 300           |
| `cluster_name`  | 120 / 130 / 140 / 200           |
| `status`        | 80 / 90 / 100 / 110 / 120       |
| `bk_cloud_id`   | 100 / 120 / 130 / 140（+width 150） |
| `db_module_id`  | 100 / 150                       |

`master_domain` 逐个来源：tendbha `minWidth: 280`、tendbha-slave `minWidth: 280`、tendb-single `minWidth: 250`、
tendb-cluster `minWidth: 300`、redis `minWidth: 250`、mongo `minWidth: 250`、sqlserver-single `width: 280`、
sqlserver-ha `width: 240`、oracle-single `width: 280`、oracle-ha `width: 240`。前六个可伸缩，后四个写死。

`redis/Index.vue:316-328` 的 `bk_cloud_id` 同时写了 `minWidth: 120` 与 `width: 150`。

### 2. 共享列组件内部同样不一致

- `views/db-manage/common/cluster-table/ClusterNameColumn.vue:6` 是 `:min-width="200"`，而
  `instance-table/ClusterNameColumn.vue:70` 是 `window.innerWidth < 1366 ? 180 : 280`。同一个「集群名称」列两套取值。
- `cluster-table/MasterDomainColumn.vue:83` 响应式 180/280，`cluster-table/SlaveDomainColumn.vue:5` 固定
  280。主从域名列出现在同一张表里，窗口宽度 <1366 时主域名 180、从域名 280。

### 3. 魔法断点重复且不响应 resize

`window.innerWidth < 1366 ? A : B` 在 5 处逐字重复：`cluster-table/MasterDomainColumn.vue:83`、
`instance-table/MasterDomainColumn.vue:70`、`instance-table/InstanceDomainColumn.vue:69`、
`instance-table/ClusterNameColumn.vue:70`（以上均 180/280）、`instance-table/InstanceAddressColumn.vue:74`（150/200）。

它们是 setup 期一次性求值的普通常量，窗口 resize 后不会更新。

## 项目里已有的正确做法

`views/db-manage/common/cluster-table/` 与 `instance-table/` 是「一列一个组件」的写法，宽度、表头复制、筛选都封装在列组件内部。bigdata
列表页（kafka / hdfs / es / pulsar / riak）全部通过 `MasterDomainColumn` 渲染 `master_domain`，因此这批页面天然一致。

**不一致集中在没走这套抽象的地方**：cluster-selector、instance-selector、工具箱预览表、单据详情表。所以问题不是「缺一张列宽表」，而是列组件抽象只覆盖了列表页，没覆盖弹窗与选择器。

## 建议方向（未采纳）

- 不建议按字段名建 `Record<field, number>`：字段会无限膨胀，且同字段不同 label 时失准（`master_domain` 在 pulsar 叫「访问入口」、riak 叫「主访问入口」）
- 倾向按内容语义分档的宽度令牌（域名类 / 名称类 / 状态与数字类 / 操作类），把 1366 断点一并收进去，列组件消费令牌而非魔法数字
- 注意跨容器不宜强求同宽：全屏列表页与 `max-height: 472` 的选择器弹窗可用宽度本就不同，硬套大值会挤出横向滚动

## 待查证

- 未做全项目扫描。仓库内 202 个文件含 `TableColumn`、66 个文件含 `colKey`，本篇只覆盖 cluster-selector 与
  `db-manage/common` 两处列组件
- 弹窗宽度档位、分页默认 limit、状态色映射、时间格式化是否存在同类漂移，属于推断，未验证
