# 行编辑、批量录入与资源标签踩坑指南

## 行编辑与回填的三类易错点

### 1. 集群域名解析触发时机

`ClusterColumn` 的 watch 条件是 `master_domain && !id`，只有**手输域名**（内部置 `id: 0`）才发请求反查；通过集群选择器选择（`batch-edit`）不会触发。需要「选完集群做联动」的逻辑挂在 `@request-success`（仅手输解析成功触发）不够——选择器路径需要单独处理。

### 2. 联动清空的防误清模式

行数据带 `xxx_domain` 归属标记，仅当关联字段真正变化时才清空。典型场景：库映射列随源集群变化清空，但批量录入预置了映射后域名解析成功会误清。解法：

```typescript
// 仅当源集群真正变化时才清空库映射，避免回填/批量录入后域名解析成功把映射误清掉
const handleSourceClusterChange = (row: RowData) => {
  if (row.db_mapping_domain !== row.source_cluster.master_domain) {
    Object.assign(row, { db_mapping: [] });
  }
  Object.assign(row, { db_mapping_domain: row.source_cluster.master_domain });
};
```

### 3. 对象数组字段的边界转换

后端字段若是 `{ db: string; table: string }[]` 这类对象数组（如 `do_tables`、`ignore_tables`），UI 层列组件（`DbNameColumn`/`TableNameColumn` 的 `modelValue` 是 `string[]`）不要直接改列组件类型，在提单/回填边界做转换：

```typescript
// 回填：对象数组 → 字符串列表
source_table_list: (sync_scope.do_tables || []).map((tableItem) => tableItem.table),

// 提交：字符串列表 × DB 列表 → 对象数组（flatMap 笛卡尔积组装）
do_tables: item.source_db_list.flatMap((db) => item.source_table_list.map((table) => ({ db, table }))),
```

## 批量录入（BatchInput）六条约定

1. `batchInputConfig` 的 `key` 是**行数据字段名**（camelCase 前端字段），不是后端字段名——例如 `source_master_domain`、`spec_name`，解析后写入 `source_cluster.master_domain`、`spec_id`
2. **示例文本禁止包含会被按空白符误切的分隔符**：批量录入按空白符（换行/空格/Tab）切列，示例里含空格的值（如 `source_db target_db`）会被切到下一列导致整行错位。映射对用冒号 `source_db:target_db`，多条用逗号分隔
3. 多值字段解析：DB/表列表按 `\n` 拆分（`item.source_db_list.split('\n')`）；标签按逗号拆分为 `{ value }` 数组（`item.labels.split(',').map((label) => ({ value: label }))`），需补类型断言 `as RowData['labels']`
4. 规格列：录入规格名（如 `2核_4G_50G`）传入 `spec_id` 字段，`SpecColumn` 检测到字符串时按规格名自动匹配转 ID（与 `MYSQL_PROXY_MIGRATE_INS` 等存量单据同机制），匹配失败自动清空该格
5. 覆盖模式（`isClear`）下 `tableKey.value = random()` 强制重挂载表格，`setTimeout(() => tableRef.value?.validate(), 200)` 触发校验
6. 追加模式的起始行判断：`[...(formData.tableData[0].source_cluster.id ? formData.tableData : []), ...dataList]`，首行未选集群时丢弃空行

## ResourceTagColumn 回填与批量录入标签

**再次提单回填**（`useTicketDetail` 回填块内）：

```typescript
// labels 是 id 列表，配合 label_names 补名称，ResourceTagColumn 的 updateModel 按 id/value 命中 tagMap 回显
labels: (item.resource_spec?.master?.labels || []).map((labelId, index) => ({
  id: Number(labelId),
  value: item.resource_spec?.master?.label_names?.[index] || '',
})) as RowData['labels'],
```

提交时对称回传：`label_names: item.labels.map((label) => label.value)`、`labels: item.labels.map((label) => String(label.id))`。

**已知组件坑（已修复）**：`resource-tag-column/Index.vue` 曾存在竞态缺陷——批量录入覆盖模式下表格重挂载，`watch(modelValue)` 不带 `immediate` 不执行导致 `ids` 为空，200ms 后自动校验把 `modelValue` 清空，标签列表异步返回后被重置为「通用无标签」。修复方式：`watch(tagList)` 在 `modelValue` 有值时调用 `updateModel` 回填；校验规则加保护（`ids` 未回填且 `modelValue` 有值时不清空）。若发现「批量录入标签不可用/丢失」，先查该组件是否回退。
