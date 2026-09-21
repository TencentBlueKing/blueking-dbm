# 单据详情组件

位置、工厂匹配规则、命名对照见 [registry.md](registry.md)。本篇写怎么把一个 `details` 渲染出来。

## 只写 com-factory 下那一个组件

`ticket-center/common/ticket-detail/Index.vue` 是壳，按 `ticketId` 拉详情后渲染三段：`BaseInfo`（全单据通用）、
`task-info` → `com-factory` 按 `ticket_type` 分发（**要写的就是这块**）、`flow-info`（按 flow 类型分发）。
底栏的「再次提单」/ 撤销 / 终止也由壳提供。

```vue
<script setup lang="ts">
  import TicketModel from '@services/model/ticket/ticket';
  import type { Mysql } from '@services/model/ticket/ticket';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.Xxx>;
  }

  defineOptions({
    name: TicketTypes.MYSQL_XXX,
    inheritAttrs: false,
  });
</script>
```

- `InfoList` 的相对深度跟组件位置走：`{db}/Xxx.vue` 是 `../components/...`，`{db}/{子目录}/Index.vue` 是 `../../`
- `TicketInfoTable` / `TicketInfoTableColumn` 全局已注册（`src/common/importComps.ts`），不要 import
- 数组字段用 `TagBlock`（`@components/tag-block/Index.vue`），需要整列复制的加 `get-copy-value`
- 存量的 `ticket-details-list` div 是旧写法，只剩 3 处，新代码不要用

## 按详情结构选形态，不硬套

- **纯表格型**（无页级表单项）：`TicketInfoTable` 直接作模板根。多数 mongodb 组件如此（`DataExport`、`ReduceMongos`）
- **带页级表单项**（模式、开关、布尔）：`InfoList` 在前逐项展示，表格在后，**顺序与提单入口一致**
  （`InstanceReload`、`redis/ProxyScaleDown`）
- **模式型**：`InfoList` 展示模式字段后用 `v-if` 切多张表（`InstanceReload` 三张）。**详情组件允许 `v-if`**，
  不受工具箱提单页「模式必须拆动态组件」的约束——只读展示没有行模型和校验纠缠

## 列数据的来源约束

**每一列都必须能说清来自哪个 `details` 字段，或由哪些字段演算得到。不得臆造字段名或自造合并叫法。**

允许聚合展示（`ReduceMongos` 把 nodes 拼成 IP 列表）和只读演算（`ReduceShardNodes` 的「缩容至」= 当前 − 缩容数）。
建议先 map 成展示行再绑 `col-key`，比在模板里堆表达式好读。**展示字段与提单入口的可编辑字段一一对应。**

## 取值兜底

- **集群域名**：`details.clusters` 可能未注入，必须 `details.clusters?.[id]?.immute_domain || '--'`，直接索引会白屏
- **规格名**：在顶层 `details.specs` 里，**不在** `resource_spec.master.spec_name`（后端实际不返回）。
  取 `details.specs?.[item.resource_spec?.master?.spec_id]?.name || ''`
- **空值**：空数组、缺失域名统一 `--`，不与 `-` 混用
- **资源标签**：渲染 `resource_spec.master.label_names`，空时显示绿色「通用无标签」`DbTag`（`theme="success"`）

## 两个容易翻车的细节

**行键**：`row-key` 用行标识字段（如 `source_cluster`），**不要用后端生成的 `task_name`**——旧单据可能没这字段。

**交互入口位置**：侧滑等点击入口放**单元格本身**，**不要放表头插槽**。表头整列只渲染一次，`@click` 闭包永远捕获
第一行数据，症状是「点了没反应 / 点开的永远是第一行」。

## 长列表折叠

多值列默认显示前 5 个标签，超出追加「共 N 个」，点击展开变「收起」。展开状态按行独立管理：

```typescript
const expandedKeys = ref(new Set<string>());
const handleToggleExpand = (row: RowData) => {
  const key = String(row.source_cluster);
  const newSet = new Set(expandedKeys.value);
  newSet.has(key) ? newSet.delete(key) : newSet.add(key);
  expandedKeys.value = newSet;
};
```

联动列（如库映射）显示首条 + 总条数（`order_db → order_archive 共 3 条`），蓝色可点击打开侧滑。用
`EditableBlock` 默认插槽自定义渲染，`:model-value` 绑摘要字符串保证列校验仍触发。
