# 表格列宽优先 min-width，取值落在约定档位

- **命中**：本次新增或改了 `TableColumn` 的 `width` / `min-width`（不含工具箱 `EditableColumn`）
- **为什么**：`width` 钉死列宽，窗口变宽时剩余空间堆到最后几列或出现横向滚动；同表再混用
  `min-width` 与 `width`（主域名 `min-width: 180` 配从域名 `width: 280`）会一个撑开一个撑不开
- **改成**：新列写 `:min-width`，数字对照 `.agents/skills/dbm-designer/list-page.md`「列宽约定」。
  已有 `col-key` 先 `rg -A3 'col-key="<字段名>"' src`（或 `colKey: '<字段名>'`）取现有数字，属性仍用
  `min-width`。只有操作图标列 30、选择列 80 才写 `width`。只改本次碰到的列
- **不要**新列写 `width`（上述两列除外）。不要按字段名建 `Record<field, number>`。不要跨容器强求同宽：
  全屏列表页与 `max-height: 472` 的选择器弹窗可用宽度本就不同。存量 `width` 不要顺手改
- **存量**：`*Column.vue` 里 `width` 约 74 处、`min-width` 约 152 处（2026-09-21）。数字不一致集中在没走列
  组件抽象的地方——`cluster-selector`、`instance-selector`、工具箱预览表、单据详情表。公共列内部也不一致：
  集群表 `ClusterNameColumn` 是 `:min-width="200"`，实例表同名列是 `window.innerWidth < 1366 ? 180 : 280`；
  集群表 `create_at` 是 `width: 180`，实例表是 `140`
- **核实**：2026-09-21

## 补充

`src/views/db-manage/common/cluster-table/` 与 `instance-table/` 是「一列一个组件」的写法，宽度、表头、筛选都封装在列组件内部，bigdata
列表页（kafka / hdfs / es / pulsar / riak）全部通过 `MasterDomainColumn` 渲染 `master_domain`，这批页面天然一致。问题不是「缺一张列宽表」，而是列组件抽象只覆盖了列表页，没覆盖弹窗与选择器。

`window.innerWidth < 1366 ? A : B` 只允许出现在域名类列（及实例地址）。命令：

```bash
rg -n 'innerWidth < 1366' src
```

当前 5 处：`cluster-table/MasterDomainColumn.vue`，`instance-table/` 下 `MasterDomainColumn` /
`InstanceDomainColumn` / `InstanceAddressColumn` / `ClusterNameColumn`。都是 setup 期一次性求值，窗口
resize 后不会更新；新列同样即可，不要为此加 resize 监听。
