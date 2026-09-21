# 三类页面骨架与扩展点

集群列表、集群详情、实例列表都有公共骨架，各 DB 页面只负责「传 `clusterType` + 传 `dataSource` + 填 slot」。
**不要另起一套骨架**，需要的差异化优先看有没有现成 slot，没有就在公共组件里按字段名加 slot。

## 集群列表

### 骨架

```vue
<template>
  <div class="xxx-list-page">
    <div class="operation-box">
      <!-- 申请、批量操作、导出、授权等入口 -->
      <DbQuickSearch v-model="searchValue" class="quick-search" :data="quickSearchData" parse-url
        @change="handleQuickSearchChange" />
    </div>
    <ClusterTable
      ref="clusterTable"
      :bk-ui-settings="settings"
      :cluster-id="clusterId"
      :cluster-type="ClusterTypes.XXX"
      :data-source="getXxxList"
      :filter-value="searchValue"
      @bk-ui-settings-change="updateTableSettings"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <template #operation>…</template>
      <template #masterDomain>…</template>
    </ClusterTable>
    <TableDetailDialog v-model="isShowDetail" :default-offset-left="300" @close="handleDetailClose">
      <ClusterDetail v-if="clusterId" :cluster-id="clusterId" />
    </TableDetailDialog>
  </div>
</template>
```

配套 hooks（都从 `@hooks` 导入）：

| hook | 作用 |
| --- | --- |
| `useClusterQuickSearch(clusterType)` | 出 `searchValue` / `quickSearchData` / `isSearching`，与列筛选、URL 同步 |
| `useTableSettings(UserPersonalSettings.XXX_TABLE_SETTINGS, { disabled: [...] })` | 列显隐持久化 |
| `useClusterTableSelect<Model>()`（`@views/db-manage/hooks/`） | 多选状态，出 `selectedList` / `selectedIdList` / `isSelected` |
| `useGoClusterDetail('XxxDetail')`（同上） | 抽屉开关 + URL `clusterId` 同步，出 `clusterId` / `showDetail` / `goClusterDetail` |
| `useOperateClusterBasic(clusterType, { onSuccess })`（`common/hooks/`） | 启用 / 禁用 / 删除，含二次确认弹窗与提单 |

刷新一律 `tableRef.value!.fetchData(searchValue.value)`，`@filter-change` 里把 `filterValue` 写回
`searchValue` 再刷新——搜索栏与列筛选是同一份状态，细节见 `dbm-frontend-developer` 的 `references/search-filter-sync.md`。

### `ClusterTable` 的扩展点

Props：`clusterType`（必填，驱动列筛选项与 k8s 分流）、`clusterId`（必填，高亮当前详情行 + 控制 k8s 轮询启停）、
`dataSource`（必填）、`bkUiSettings`、`disableSelectMethod`、`filterValue`。其余属性 `v-bind="$attrs"` 透传 `DbTable`。

Expose：`fetchData(params)`、`getData()`、`getAllData()`、`removeSelectByKey(key)`。

固定内置、**不要在业务页重复实现**的列：`IdColumn`、`ClusterAliasColumn`、`CommonColumn`
（版本、容灾级别 / 地域、规格、管控区域、创建人、部署时间、时区）。

Slot 与默认实现：

| slot | 默认 | 说明 |
| --- | --- | --- |
| `operation` | 无 | 操作列，放 `OperationColumn`，其 `#default="{ data }"` 给行数据 |
| `masterDomain` | 无 | 主访问入口，放 `MasterDomainColumn`；大数据类传 `field="domain"` 并改 label 为「访问入口」 |
| `slaveDomain` | 无 | 从访问入口 |
| `clusterTag` | `ClusterTagColumn` | 标签 |
| `status` | `StatusColumn` | 状态 |
| `clusterState` | `ClusterStatsColumn` | 容量使用率，**`clusterType.includes('k8s')` 时整列不渲染** |
| `role` | 无 | 角色节点，一个角色一个 `RoleColumn field="xxx"`，可用 `#nodeTag` 标记节点 |
| `clusterTypeName` / `syncMode` / `moduleNames` | 无 | 架构版本 / 同步模式 / 所属模块 |

列组件从 `cluster-table/Index.vue` 具名导出，不要深入子路径 import：

```ts
import ClusterTable, { MasterDomainColumn, OperationColumn, RoleColumn } from '@views/db-manage/common/cluster-table/Index.vue';
```

**新增一列的顺序**：先按 [feature-scope.md](feature-scope.md) 定范围。全部 → 改 `CommonColumn.vue`；
一类或某一个 → 先确认有没有对应 slot，没有就在 `cluster-table/Index.vue` 按字段名加**空** slot，再只在
名单内的业务页实现。不要因为 mysql 列表有某列，就写进 `CommonColumn`。

### 周边能力

| 能力 | 组件 | 挂法 |
| --- | --- | --- |
| 批量启停 / 删除 / 标签 | `common/cluster-batch-opration/` | 列表 header，传 `cluster-type`、`selected`，监听 `@success` |
| 导出 Excel | `common/dropdown-export-excel/` | 列表 header，传 `type`（clusterType）、`ids` |
| 集群授权 | `common/cluster-authorize/` | `v-model` 控制侧滑，传 `accountType`、`clusterTypes`、`selected` |
| 告警订阅 | `common/cluster-alarm-subscribe/` | 行操作菜单内，`@edit` 跳详情告警 Tab |
| 访问方式 | `common/cluster-entry-panel/` | `MasterDomainColumn` 的 `#append` |
| webconsole | 独立路由页 | 列表用 `AuthRouterLink` 跳过去 |

## 集群详情

### 双入口分层

```
{db}/common/{架构}-cluster-detail/Index.vue   实现：DisplayBox + ActionPanel，props 只有 clusterId
{db}/{架构}-cluster-detail/Index.vue           路由壳：读 route.params.clusterId + defineExpose({ routerBack })
{db}/{架构}-cluster-list/Index.vue             抽屉：TableDetailDialog 里直接挂 common 下的实现
```

路由壳全文就这么几行，不要往里塞业务：

```vue
<template>
  <ClusterDetail :cluster-id="clusterId" />
</template>
<script setup lang="ts">
  import ClusterDetail from '../common/ha-cluster-detail/Index.vue';

  const route = useRoute();
  const router = useRouter();
  const clusterId = Number(route.params.clusterId);

  defineExpose({
    routerBack() {
      router.push({ name: 'XxxHaList' });
    },
  });
</script>
```

大数据类目录名是 `detail/` 和 `common/cluster-detail/`，分层是同一套。

### `ActionPanel` 的 Tab

Props：`clusterData`、`clusterType`、`clusterRoleNodeGroup`。Tab 由它统一给，业务页只覆盖 slot：

| slot | 默认 Tab | 备注 |
| --- | --- | --- |
| `topo` | 集群拓扑 | |
| `info` / `infoContent` | 基本信息 | 绝大多数 DB 只覆盖 `infoContent` 换成带 slot 的 `BaseInfo` |
| `instance` / `instanceContent` | 实例列表 | 大数据换 `BigDataInstanceList`，K8s 换 `K8SInstanceList` |
| `host` / `hostContent` | 主机列表 | **`clusterType.includes('k8s')` 时整个 Tab 不渲染** |
| `paramConfig` | 参数配置 | 同上，K8s 无 |
| `record` | 单据记录 | 同上，K8s 无 |
| `operation` | 操作记录 | **只有 K8s 有** |
| `alarmSubscription` | 告警订阅 | 该 clusterType 有监控指标时才出现 |

监控仪表盘 Tab 由 `getMonitorUrls` 动态生成，`ActionPanel` 内有一份「暂时没数据、不请求」的 clusterType
黑名单，新 DB 后端仪表盘没就绪时加进去，就绪后删掉。

`BaseInfo` 的可覆盖 slot：`clbMaster`、`clbSlave`、`polaris`、`slaveDomain`、`moduleName`、`moduleNames`、
`clusterTypeName`、`syncMode`、`spec`、`load`、`coldResource`、`k8sClusterName`。

Tab 切换状态写在 URL query 上，**不要另外用 ref 记当前 Tab**。

## 实例列表

`common/instance-table/Index.vue`，形态与 `cluster-table` 一致，差异：

- Props 没有 `clusterId`；`disableSelectMethod` 可返回 `string` 当禁用原因
- 多一个 `requestSuccess` emit，带整包 `ListBase<InstanceModel[]>`
- slot：`operation`、`instanceAddress`、`domain`、`shard`、`relatedCluster`、`ip`、`mongodbState`
- 公共列在 `instance-table/CommonColumn.vue`（状态、角色、版本、园区、OS、部署时间）
- 搜索用 `useInstanceQuickSearch`

大数据与 K8s 类没有独立实例列表页，实例只在详情 Tab 里看。

## 申请页

申请页文件放在 `{db}/{TICKET_TYPE}_APPLY/Index.vue`（在 db-manage 下），但**路由注册在
`src/views/service-apply/routes.ts`**，用 `createApplyRoute(DBTypes.X, TicketTypes.X_APPLY, t('...'))`；
入口卡片在 `src/views/service-apply/index/Index.vue` 的 `services` 数组，靠 `controllerId` 过滤显示。

大数据类的主机选择统一用 `common/big-data-host-table/RenderHostTable.vue`；K8s 类用自己的
`components/AddonSpecPlan.vue` 拉 addon 规格方案。

## influxdb 例外

influxdb 没有集群维度，列表是 `BkResizeLayout`（左侧分组树 + 右侧 `DbTable`），详情是
`BkResizeLayout` + `DbCard` + `BkTab`，三个公共骨架一个都不用。改 influxdb 只参考 influxdb 自己。
