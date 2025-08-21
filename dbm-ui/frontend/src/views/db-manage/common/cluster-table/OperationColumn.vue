<template>
  <BkTableColumn
    class-name="cluster-list-operation-column"
    fixed="left"
    label=" "
    :resize="false"
    :width="30">
    <template #default="{ data, rowIndex }: { data: IRowData; rowIndex: number }">
      <OperationMenu
        :style="{
          display: !currentClusterId ? (rowIndex === 0 ? 'flex' : '') : currentClusterId === data.id ? 'flex' : '',
        }"
        @show="() => handleShow(data)">
        <slot v-bind="{ data }" />
      </OperationMenu>
    </template>
  </BkTableColumn>
</template>
<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useRoute } from 'vue-router';

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

  const route = useRoute();

  const currentClusterId = ref(0);

  watch(
    route,
    () => {
      const currentClusterIdFromRoute = Number(route.params.clusterId);

      if (currentClusterIdFromRoute > 0) {
        currentClusterId.value = currentClusterIdFromRoute;
      }
    },
    {
      immediate: true,
    },
  );

  const handleShow = (data: IRowData) => {
    currentClusterId.value = data.id;
  };

  onBeforeUnmount(() => {
    currentClusterId.value = 0;
  });
</script>
<style lang="less">
  td.cluster-list-operation-column {
    .vxe-cell {
      padding: 0 !important;
    }
  }
</style>
