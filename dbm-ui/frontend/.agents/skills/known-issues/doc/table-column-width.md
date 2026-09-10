# 新增表格列不要再造一个宽度取值

- **命中**：给一个已在别处出现过的 colKey（`master_domain`、`cluster_name`、`status`、`bk_cloud_id`、`db_module_id`…）写新宽度；或同一张表里对同类列混用
  `width`（固定宽）与 `minWidth`（可伸缩）
- **为什么**：混用比数字不一致影响更大——主域名 `minWidth: 180` 配从域名 `width: 280`
  出现在同一张表里，窗口宽度变化时一个撑开一个撑不开；同一个域名列在一个弹窗里能撑开、在另一个里撑不开
- **改成**：先 `rg -A3 "colKey: '<字段名>'" src` 看现有取值，取其中之一，不新造；同表同类列统一用
  `minWidth`。**全局统一方案未定，存量不要动**
- **不要**按字段名建 `Record<field, number>`：字段会无限膨胀，且同字段不同 label 时失准（`master_domain` 在
  pulsar 叫「访问入口」、riak 叫「主访问入口」）。也**不要**跨容器强求同宽：全屏列表页与
  `max-height: 472` 的选择器弹窗可用宽度本就不同，硬套大值会挤出横向滚动
- **存量**：不一致集中在没走列组件抽象的地方——`cluster-selector`、`instance-selector`、工具箱预览表、单据详情表
- **核实**：2026-09-10

## 补充

`src/views/db-manage/common/cluster-table/` 与 `instance-table/` 是「一列一个组件」的写法，宽度、表头、筛选都封装在列组件内部，bigdata
列表页（kafka / hdfs / es / pulsar / riak）全部通过 `MasterDomainColumn` 渲染 `master_domain`，这批页面天然一致。问题不是「缺一张列宽表」，而是列组件抽象只覆盖了列表页，没覆盖弹窗与选择器。

共享列组件内部也不一致：`cluster-table/ClusterNameColumn.vue` 是 `:min-width="200"`，
`instance-table/ClusterNameColumn.vue` 是 `window.innerWidth < 1366 ? 180 : 280`。

`window.innerWidth < 1366 ? A : B` 逐字重复 5 处（`rg -n 'innerWidth < 1366' src`：`cluster-table/MasterDomainColumn.vue`
与 `instance-table/` 下 4 个列组件），且都是 setup 期一次性求值的普通常量，窗口 resize 后不会更新。

倾向按内容语义分档的宽度令牌（域名类 / 名称类 / 状态与数字类 / 操作类），把 1366 断点一并收进去。
