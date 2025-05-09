<template>
  <BkTableColumn
    class-name="cluster-list-operation-column"
    fixed="left"
    label=" "
    :resize="false"
    :width="30">
    <template #default="{ data, rowIndex }: { data: IRowData; rowIndex: number }">
      <OperationMenu :style="{ display: rowIndex === 0 ? 'flex' : '' }">
        <slot v-bind="{ data }" />
      </OperationMenu>
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import OperationMenu from './components/OperationMenu.vue';
  import type { ClusterModel, ISupportClusterType } from './types';

  export interface Props<T extends ISupportClusterType> {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: T;
  }

  export interface Slots<T extends ISupportClusterType> {
    default: (params: { data: ClusterModel<T> }) => void;
  }

  type IRowData = ClusterModel<T>;

  defineProps<Props<T>>();

  defineSlots<Slots<T>>();
</script>
<style lang="less">
  td.cluster-list-operation-column {
    .vxe-cell {
      padding: 0 !important;
    }
  }
</style>
