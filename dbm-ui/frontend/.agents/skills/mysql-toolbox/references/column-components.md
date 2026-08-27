# 列组件与表单项清单

## MySQL 专属列组件

路径前缀：`@views/db-manage/mysql/common/toolbox-field/`

| 组件 | 路径 | 用途 |
|------|------|------|
| `ClusterColumn` | `cluster-column/Index.vue` | **首列**源集群选择，支持 `cluster-types`、`allow-repeat`、`selected` |
| `DbNameColumn` | `db-name-column/Index.vue` | DB 名输入，支持 `cluster-id` 联动、`check-not-exist`（校验 DB 是否在集群中不存在）、`field` |
| `TableNameColumn` | `table-name-column/Index.vue` | 表名输入，同 DbNameColumn 接口 |
| `TargetClusterColumn` | `target-cluster-column/Index.vue` | **非首列**目标集群选择（单目标），见下方详解 |
| `MultipleClusterColumn` | `multiple-cluster-column/Index.vue` | 多集群选择 |
| `WithRelatedClustersColumn` | `with-related-clusters-column/Index.vue` | 集群选择（含关联集群） |

## TargetClusterColumn 详解

当表格中需要选择**目标集群**（非首列的源集群）时，**不能直接用 `ClusterColumn`**，应使用 `TargetClusterColumn`。

**参考实现**：`MYSQL_FIXPOINT_EXIST_CLUSTER/components/target-cluster-column/Index.vue`（原始实现），`@views/db-manage/mysql/common/toolbox-field/target-cluster-column/Index.vue`（已提取的公共版本）

特征：

- `EditableInput` + `#append` 插槽放 `DbIcon`（`type="host-select"`）触发 `ClusterSelector`
- `ClusterSelector` 支持 `TENDBHA` + `TENDBSINGLE`，`multiple: false`
- `disabledRowConfig` 排除源集群（提示「不能选择源集群」）
- `disabledMethod`：源集群未选时禁用目标集群列，提示「请先选择源集群」
- 手动输入域名时清空 `id`，通过 `watch` + `filterClusters` API 自动查询补全
- 校验规则：域名格式（`domainRegex`）、目标集群重复、目标集群不存在

Props：

```typescript
interface Props {
  cluster: { id: number; master_domain: string };  // 源集群信息
  field?: string;           // 默认 'target_cluster.master_domain'
  selected: { id: number; master_domain: string }[]; // 已选目标集群（去重校验）
  sourceField?: string;     // 默认 'source_cluster'，用于 disabledMethod 判断
}
```

**复用决策**：

1. 优先使用公共版本 `@views/db-manage/mysql/common/toolbox-field/target-cluster-column/Index.vue`
2. 如需定制（多目标集群等），在当前单据 `components/` 下独立实现，参考 `MYSQL_DATA_MIGRATE/components/TargetClusterColumn.vue`

## 跨库通用列组件

路径前缀：`@views/db-manage/common/toolbox-field/column/`

| 组件 | 路径 | 用途 |
|------|------|------|
| `OperationColumn` | `operation-column/Index.vue` | 行操作列（增删行），**必须包含** |
| `SpecColumn` | `spec-column/Index.vue` | 规格选择 |
| `ResourceTagColumn` | `resource-tag-column/Index.vue` | 资源标签（回填/批量录入坑见 [row-editing-pitfalls.md](row-editing-pitfalls.md)） |
| `AvailableResourceColumn` | `available-resource-column/Index.vue` | 可用资源展示 |
| `MultipleResourceHostColumn` | `multiple-resource-host-column/Index.vue` | 多主机选择 |
| `SingleResourceHostColumn` | `single-resource-host-column/Index.vue` | 单主机选择 |
| `DbTableNameColumn` | `db-table-name-column/Index.vue` | DB + 表名组合输入 |

## 跨库通用表单项

路径前缀：`@views/db-manage/common/toolbox-field/form-item/`

| 组件 | 路径 | 用途 |
|------|------|------|
| `TicketPayload` | `ticket-payload/Index.vue` | 备注输入，**必须包含**，导出 `createTicketPayload` 工厂函数 |
| `BackupSource` | `backup-source/Index.vue` | 备份源选择（本地/远程） |

## 模式选择组件

路径：`@components/db-card-checkbox/CardCheckbox.vue`

用于回档方式、迁移方式等卡片式单选。参考 `MYSQL_ROLLBACK/Index.vue`。Props：`modelValue`、`true-value`、`icon`、`title`、`desc`。
