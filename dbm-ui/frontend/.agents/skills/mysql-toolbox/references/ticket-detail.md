# 单据详情页实现（与原型对齐）

详情页组件结构与取值约定（参考 `DtsDataMigrate.vue`、`DtsDataMigrateRename.vue`）。

**结构**：`InfoList`/`InfoItem`（页级信息，如数据冲突处理）+ `TicketInfoTable`/`TicketInfoTableColumn`（行级表格）。

## 取值兜底（三类）

- 集群域名：`details.clusters` **可能未注入**（后端单据类型未 `patch_cluster_details` 时缺失），必须 `details.clusters?.[id]?.immute_domain || '--'`，直接索引会 `TypeError` 白屏
- 规格名：规格名在顶层 `details.specs` 映射里，**不在** `resource_spec.master.spec_name`（该字段实际不返回）。取值 `details.specs?.[item.resource_spec?.master?.spec_id]?.name || ''`
- 空列表占位：空数组显示 `--`（统一口径，勿与 `-` 混用）；集群域名兜底同为 `--`

## 资源标签列

渲染 `resource_spec.master.label_names`，空时显示绿色「通用无标签」DbTag（`theme="success"`），与 kafka/ES 等详情组件口径一致。

## 长列表折叠展开

源 DB 等多值列：默认显示前 5 个标签，超出追加「共 N 个」标签，点击展开全部变为「收起」；展开状态按行（`row-key` 字段值）用 `expandedKeys: Set<string>` 独立管理：

```typescript
const expandedKeys = ref(new Set<string>());
const handleToggleExpand = (row: RowData) => {
  const key = String(row.source_cluster);
  const newSet = new Set(expandedKeys.value);
  newSet.has(key) ? newSet.delete(key) : newSet.add(key);
  expandedKeys.value = newSet;
};
```

## 联动列的显示形态

库映射类单元格：单元格显示首条映射 + 总条数（`order_db → order_archive 共 3 条`），蓝色可点击打开侧滑——用 `EditableBlock` 默认插槽自定义渲染，`:model-value` 绑定映射摘要字符串保证列校验仍触发。

## 多行归属列的行键

`TicketInfoTable` 的 `row-key` 用行标识字段（如 `source_cluster`），不用后端生成的 `task_name`（旧单据可能没有）。

## 编辑入口位置

侧滑触发放在**单元格本身**（`EditableBlock` 点击），不放表头插槽——表头整列只渲染一次，`@click` 闭包永远捕获第一行数据，表现为「点不开」。
