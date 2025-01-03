<template>
  <BaseRoleColumn
    v-bind="props"
    :key="field" />
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import DbTable from '@components/db-table/index.vue';

  import BaseRoleColumn from './components/base-role-column/Index.vue';
  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType> {
    field: string;
    label: string;
    searchIp?: string[];
    clusterType: clusterType;
    selectedList: ClusterModel<clusterType>[];
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
  }

  export interface Slots {
    nodeTag: (params: { data: { ip: string; port: number; status: string } }) => void;
  }

  const props = defineProps<Props<T>>();
  defineSlots<Slots>();
</script>
