<template>
  <DbTable
    ref="tableRef"
    class="db-cluster-table"
    :data-source="dataSource"
    :disable-select-method="disableSelectMethod"
    releate-url-query
    :row-class="getRowClass"
    :row-config="{
      useKey: true,
      keyField: 'id',
    }"
    :scroll-y="{ enabled: true, gt: 0 }"
    selectable
    :show-overflow="false"
    show-settings
    @selection="handleSelection">
    <slot name="operation" />
    <slot name="masterDomain" />
    <slot name="clusterName">
      <ClusterNameColumn
        :cluster-type="clusterType"
        :get-table-instance="getTableInstance"
        :is-filter="isFilter"
        :selected-list="selected"
        @refresh="handleRefresh" />
    </slot>
    <slot name="slaveDomain" />
    <slot name="clusterTag">
      <ClusterTagColumn :cluster-type="clusterType" />
    </slot>
    <slot name="status">
      <StatusColumn :cluster-type="clusterType" />
    </slot>
    <slot name="clusterState">
      <ClusterStatsColumn :cluster-type="clusterType" />
    </slot>
    <slot name="role" />
    <slot name="clusterTypeName" />
    <slot name="syncMode" />
    <slot name="moduleNames" />
    <CommonColumn :cluster-type="clusterType" />
  </DbTable>
</template>
<script lang="ts">
  import type { VNode } from 'vue';

  import ClusterNameColumn from './ClusterNameColumn.vue';
  import ClusterStatsColumn from './ClusterStatsColumn.vue';
  import ClusterTagColumn from './ClusterTagColumn.vue';
  import CommonColumn from './CommonColumn.vue';
  import IdColumn from './IdColumn.vue';
  import MasterDomainColumn from './MasterDomainColumn.vue';
  import ModuleNameColumn from './ModuleNameColumn.vue';
  import OperationColumn from './OperationColumn.vue';
  import RoleColumn from './RoleColumn.vue';
  import SlaveDomainColumn from './SlaveDomainColumn.vue';
  import StatusColumn from './StatusColumn.vue';

  export {
    ClusterNameColumn,
    ClusterStatsColumn,
    ClusterTagColumn,
    CommonColumn,
    IdColumn,
    MasterDomainColumn,
    ModuleNameColumn,
    OperationColumn,
    RoleColumn,
    SlaveDomainColumn,
    StatusColumn,
  };
</script>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import DbTable, { type Props as DbTableProps } from '@components/db-table/index.vue';

  import type { ClusterModel, ISupportClusterType } from './types.ts';

  export interface Props<C extends ISupportClusterType> {
    clusterId: number;
    clusterType: C;
    disableSelectMethod?: (data: any) => boolean;
  }

  export interface Emits<C extends ISupportClusterType> {
    (e: 'refresh'): void;
    (e: 'selection', key: number[], list: ClusterModel<C>[]): void;
  }

  export interface Expose<C extends ISupportClusterType> {
    fetchData: (params: Record<string, any>) => void;
    getData: <C>() => C[];
  }

  export interface Slots {
    clusterName: () => VNode;
    clusterState: () => VNode;
    clusterTag: () => VNode;
    clusterTypeName: () => VNode;
    masterDomain: () => VNode;
    moduleNames: () => VNode;
    operation: () => VNode;
    role: () => VNode;
    slaveDomain: () => VNode;
    status: () => VNode;
    syncMode: () => VNode;
  }

  const props = withDefaults(defineProps<DbTableProps & Props<T>>(), {
    disableSelectMethod: () => false,
  });

  const emits = defineEmits<Emits<T>>();

  defineSlots<Slots>();

  const getRowClass = (data: { id: number; isNew: boolean; isOnline: boolean }) => {
    const classList = [];
    if (data.isNew) {
      classList.push('is-new');
    }
    if (!data.isOnline) {
      classList.push('is-offline');
    }
    if (data.id === props.clusterId) {
      classList.push('is-selected-row');
    }
    return classList.join(' ');
  };

  const tableRef = ref<InstanceType<typeof DbTable>>();
  const isFilter = ref(false);
  const selected = shallowRef<ClusterModel<T>[]>([]);

  const getTableInstance = () => tableRef.value;

  const handleRefresh = () => {
    emits('refresh');
  };

  const handleSelection = (_: any, list: ClusterModel<T>[]) => {
    selected.value = list;
  };

  defineExpose<Expose<T>>({
    fetchData(params: Record<string, any>) {
      tableRef.value?.fetchData(params);
      isFilter.value = Object.keys(params).length > 0;
    },
    getData<T>() {
      return tableRef.value?.getData<T>() || [];
    },
  });
</script>
<style lang="less">
  .db-cluster-table {
    tr {
      &.is-new {
        td {
          background-color: #f3fcf5 !important;
        }
      }

      &.is-offline {
        .vxe-cell {
          color: #c4c6cc !important;
        }
      }
    }

    .is-stand-by {
      color: #531dab !important;
      background: #f9f0ff !important;
    }

    .is-primary {
      color: #531dab !important;
      background: #f9f0ff !important;
    }
  }
</style>
