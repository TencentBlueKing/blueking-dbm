<template>
  <BaseRoleColumn
    v-bind="props"
    :key="field">
    <template
      v-if="slots.default"
      #default="data">
      <slot
        name="default"
        v-bind="data" />
    </template>
    <template #nodeTag="data">
      <slot
        name="nodeTag"
        v-bind="data" />
    </template>
  </BaseRoleColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType, F extends keyof ClusterModel<T>">
  import DbTable from '@components/db-table/index.vue';

  import BaseRoleColumn from './components/base-role-column/Index.vue';
  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props<clusterType extends ISupportClusterType, F extends keyof ClusterModel<clusterType>> {
    field: F;
    label: string;
    searchIp?: string[];
    clusterType: clusterType;
    selectedList: ClusterModel<clusterType>[];
    isFilter: boolean;
    getTableInstance: () => InstanceType<typeof DbTable> | undefined;
  }

  export type ReturnArrayElement<T> = T extends (infer U)[] ? U : T;

  export interface Slots<clusterType extends ISupportClusterType, F extends keyof ClusterModel<clusterType>> {
    default?: (params: { data: ReturnArrayElement<ClusterModel<clusterType>[F]> }) => void;
    nodeTag: (params: { data: ReturnArrayElement<ClusterModel<clusterType>[F]> }) => void;
  }

  const props = defineProps<Props<T, F>>();
  const slots = defineSlots<Slots<T, F>>();
</script>
