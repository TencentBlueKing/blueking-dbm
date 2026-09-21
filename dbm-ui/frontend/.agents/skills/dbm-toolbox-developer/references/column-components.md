# 列组件

## 选用优先级

1. 全局注册：`OperationColumn`（行操作列，每张表必须有）
2. 跨 DB 公共列：`src/views/db-manage/common/toolbox-field/column/`
3. 该 DB 专属列：`src/views/db-manage/{db}/common/toolbox-field/`
4. 页面私有列：`{TICKET_TYPE}/components/`

前三层都没有才新建。新建前先确认不是「公共列缺一个 prop」——加 prop 比再造一个列好。

现有列直接 `ls` 看，别凭记忆也别信手抄的清单（会腐烂）：

```bash
ls src/views/db-manage/common/toolbox-field/column/            # 跨 DB 公共列
ls src/views/db-manage/common/toolbox-field/form-item/         # 跨 DB 公共表单项
ls src/views/db-manage/{mysql,mongodb,redis,sqlserver,tendb-cluster}/common/toolbox-field/
```

两个每页必用的公共件：`operation-column`（行操作）、`form-item/ticket-payload`（单据备注，具名导出
`createTicketPayload` 工厂，回显时传 `ticketDetail`）。模式选择卡片是
`common/db-card-checkbox/CardCheckbox.vue`。

**`oracle` 没有 `common/toolbox-field/` 目录**，要给它加表格型单据时从跨 DB 公共层取，或参照 mongodb 新建。
DBA 提单的列写在 `{db}/dba-manage/{TICKET_TYPE}/components/`，不要塞进业务工具箱的 `common/toolbox-field/`。

## 目标集群列（非首列的集群选择）

**不能直接复用 `ClusterColumn`**——那是首列源集群用的，没有「排除源集群」「源集群未选时禁用」这些行为。

mysql 有公共版本 `@views/db-manage/mysql/common/toolbox-field/target-cluster-column/Index.vue`，它做的事：
`EditableInput` + `#append` 的 `DbIcon` 触发 `ClusterSelector`；`disabledRowConfig` 排除源集群；`disabledMethod`
在源集群未选时禁用整列；手输域名时清空 `id` 并自动补全；三条校验（域名格式、重复、不存在）。

```typescript
interface Props {
  cluster: { id: number; master_domain: string };      // 源集群
  field?: string;                                      // 默认 'target_cluster.master_domain'
  selected: { id: number; master_domain: string }[];   // 已选目标集群，去重校验用
  sourceField?: string;                                // 默认 'source_cluster'，供 disabledMethod 判断
}
```

需要多目标等定制时在单据 `components/` 下独立实现，参考 `MYSQL_DATA_MIGRATE/components/TargetClusterColumn.vue`。
**其他 DB 目前没有公共的目标集群列。**

## 新建列组件

参照 `src/views/db-manage/mongodb/common/toolbox-field/cluster-column/Index.vue`：

- 取值组件包在 `EditableColumn` 内，且只能是 `Editable` 系列（见 [editable-table.md](editable-table.md)）
- 校验走 `append-rules`；数据流用 `defineModel`
- **列组件不感知页面业务**，差异化通过 props 注入（`field` / `label` / `setCurrentSpecIdMethod` 这种）
- 批量入口放 `#headAppend`，选中结果 `emits('batch-edit', list)` 上抛给页面
- 加载回调里的 `validate()` 只在查询未命中时调用
