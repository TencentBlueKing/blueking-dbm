# EditableTable 数据层、批量操作与踩坑

## 行工厂与 tableKey

- **每一行必须由行工厂生成**，页面里任何一处凭空造行都会埋雷
- **每个字段都要有默认值**。缺默认值时校验路径取不到值，这一列的规则等于失效，症状是「必填列空着也能提交」
- 复杂嵌套行用 `values: DeepPartial<IDataRow>`（参考 `MONGODB_SCALE_UPDOWN`）
- `tableKey = ref(random())` 是强刷 key，**凡整体替换 `tableData` 必须同时刷**——重置、批量录入覆盖、回填三处
  都算。不刷的症状是新数据渲染出来了但校验状态还停在旧行上。单独增删一行不需要

## 批量集群选择

```ts
const selectedMap = computed(() => Object.fromEntries(selected.value.map((cur) => [cur.master_domain, true])));

const handleClusterBatchEdit = (clusterList: MongodbModel[]) => {
  const newList = clusterList.filter((i) => !selectedMap.value[i.master_domain]).map((i) => createRowData({ cluster: i }));
  formData.tableData = [...(selected.value.length ? formData.tableData : []), ...newList];
};
```

首行还没选集群时丢弃那个空行，各 DB 一致。

列级批量编辑：列组件把入口放 `#headAppend`，选完 `emits('batch-edit', value, field)` 上抛，页面遍历所有行
`Object.assign(item, { [field]: value })`。

## 批量录入

用 `@views/db-manage/common/batch-input/Index.vue`，传 `config`，形状是
`{ case: 示例文本, key: 字段名, label: t(表头) }[]`。弹窗自带格式说明区、「覆盖表格已有数据」复选框和确定 / 取消，
页面只管配置和解析：

1. **`key` 是行数据字段名（前端驼峰），不是后端字段名**。`source_master_domain` 解析后写入
   `source_cluster.master_domain`，`spec_name` 写入 `spec_id`
2. **示例文本里不能有会被按空白符误切的值。** 批量录入按空白符（换行 / 空格 / Tab）切列，示例里含空格的值
   （如 `source_db target_db`）会被切到下一列导致整行错位。映射对用冒号，多条用逗号
3. 多值字段解析：DB / 表列表按 `\n` 拆；标签按逗号拆成 `{ value }` 数组，要补断言 `as IDataRow['labels']`
4. 规格列录入规格名（如 `2核_4G_50G`）写进 `spec_id`，`SpecColumn` 检测到字符串会按名自动匹配转 ID，匹配失败清空
5. 覆盖模式（`isClear`）刷 `tableKey` 后 `setTimeout(() => tableRef.value?.validate(), 200)` 触发校验
6. 追加模式起始行：`[...(formData.tableData[0].cluster.id ? formData.tableData : []), ...dataList]`

**`batchInputConfig` 要覆盖所有列。** 漏配的列录入后是空的，而用户以为自己全填了。

## 校验

规则走 `EditableColumn` 的 `append-rules`，validator 返回 `t()` 文案或 `true`。集群列的三条经典规则：域名格式
（`@common/regex` 的 `domainRegex`）、重复（基于 `props.selected` 计数）、存在性（`useRequest(filterClusters)` 按
`exact_domain` 查询）。

**跨列演算的校验写在「演算结果列」上**，不写在触发输入的列上，更不放到提交函数里用 `Message` 拦截。做法：`field`
取演算字段名（行模型可不声明该字段），validator 签名 `(_value, { rowData }: { rowData: IDataRow })`。参考
`MONGODB_SHARD_CUTOFF`、`TENDBCLUSTER_SPIDER_MNT_APPLY`。

### 什么时候可以手动 validate

默认交给提交时机。加载回调里只有一种情况可以：

```ts
onSuccess(data) {
  if (data.length > 0) {
    modelValue.value = data[0]!;          // 命中：回填整行模型，不要 validate
  } else {
    editableColumnRef.value?.validate();  // 未命中：这时才校验，报「集群不存在」
  }
}
```

命中后 validate 是错的，加载下拉选项后 validate 也是错的——用户还没录入的必填列会立刻标红。各 DB 的
`cluster-column` 都是这个形状。

### Editable 组件的自动校验

`Editable` 系列内部会 watch 自身 `modelValue` 触发所在列的 `validate('change')`。`EditableSelect` 单选时是原始值
（同值赋值不触发），**多选时是数组引用，内容相同的新引用也会触发**。框架层已在
`src/components/editable-table/edit/Select.vue` 和 `TagInput.vue` 加了 `_.isEqual` 守卫。

所以业务侧联动清空、回显过滤直接 `v-model` 直绑 + 正常赋值即可，**不要绕开 v-model 改用 `:model-value` +
`@change` 手动同步，也不要自己加赋值守卫**。

## EditableColumn 内只能放 Editable 系列

`EditableInput`、`EditableSelect`、`EditableTextarea`、`EditableBlock`、`EditableTagInput`、`EditableDatePicker`、
`EditableTimePicker`（都在 `src/components/editable-table/edit/`）。放 `DbSelect`、`BkInput` 会让编辑态、校验联动、
禁用态全部失效。

下拉多选用 `EditableSelect` 的 `:list` + `multiple`；只读展示用 `EditableColumn readonly` + `EditableBlock`；
选项依赖行数据或整列条件禁用走 `disabled-method`（范式见 `MONGODB_REDUCE_MONGOS/components/IpColumn.vue`）。

## 列禁用与存在校验

- **未选源集群时，依赖源集群的列全部禁用**，提示「请先选择源集群」。`DbNameColumn` / `TableNameColumn` 设了
  `check-not-exist` 时内置的 `disabledMethod` 会在 `clusterId` 为空时自动禁用
- **源 DB / 源表列传 `check-not-exist`**；**忽略 DB / 忽略表列不校验存在性**；通配符 `*` `%` `?` 不参与存在校验

## 四个回填踩坑点

这些坑的共同特征是：写错了页面照常渲染、照常提交，等用户克隆单据或批量录入时才暴露。

### 域名解析的触发时机

`ClusterColumn` 反查域名的 watch 条件是 `master_domain && !id`，**只有手动输入域名**才发请求。通过选择器选择走的
是 `batch-edit`，不发请求也不触发 `@request-success`。所以「选完集群做联动」只挂 `@request-success` 不够。

### 联动清空的防误清

某列要随源集群变化清空时，朴素实现会被「批量录入先写入值、随后域名解析成功又触发一次变化」误清。给行数据带一个
`xxx_domain` 归属标记，只有关联字段真的变了才清：

```ts
// 仅当源集群真正变化时才清空库映射，避免回填 / 批量录入后域名解析成功把映射误清掉
const handleSourceClusterChange = (row: IDataRow) => {
  if (row.db_mapping_domain !== row.source_cluster.master_domain) {
    Object.assign(row, { db_mapping: [] });
  }
  Object.assign(row, { db_mapping_domain: row.source_cluster.master_domain });
};
```

**归属标记要在回填、批量录入、侧滑确认三处同步写入**，漏一处那条路径的数据就会被下一次解析清掉。

### 对象数组字段的边界转换

后端是 `{ db, table }[]` 时**不要改列组件类型**（`DbNameColumn` 的 `modelValue` 是 `string[]`，是跨 DB 公共契约），
在边界转：

```ts
// 回填
source_table_list: (sync_scope.do_tables || []).map((t) => t.table),
// 提交：DB 列表 × 表列表笛卡尔积
do_tables: item.source_db_list.flatMap((db) => item.source_table_list.map((table) => ({ db, table }))),
```

协议本身已是 `string[]` 的（如 `MYSQL_DTS_DATA_MIGRATE` 的 `sync_scope` 四字段）直接透传。改协议时这段转换要跟着删。

### 资源标签

回填时 `labels` 是 id 列表，要配合 `label_names` 组装才能命中 `ResourceTagColumn` 的 `tagMap`，
组装代码见 `dbm-ticket-developer` 的 `references/submit-and-backfill.md`「两个高频漏点」。

**已知组件坑（已修复，会回退）**：`common/toolbox-field/column/resource-tag-column/Index.vue` 曾有竞态——批量录入
覆盖模式下表格重挂载，`watch(modelValue)` 不带 `immediate` 不执行导致 `ids` 为空，200ms 后的自动校验把
`modelValue` 清空。修复是 `watch(tagList)` 在 `modelValue` 有值时调 `updateModel`，并在校验规则里加保护。
**有人报「批量录入的标签丢了」，先查这个组件是不是被回退了。**
