<template>
  <TableColumn
    class-name="cluster-list-operation-column"
    col-key="row-operation"
    fixed="left"
    :resizable="false"
    title=" "
    :width="30">
    <template #default="{ row, rowIndex }: { row: IRowData; rowIndex: number }">
      <OperationMenu
        ref="operationMenuRef"
        :style="{
          display: !currentClusterId ? (rowIndex === 0 ? 'flex' : '') : currentClusterId === row.id ? 'flex' : '',
        }"
        @show="() => handleShow(row)">
        <slot v-bind="{ data: row }" />
      </OperationMenu>
    </template>
  </TableColumn>
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

  export interface Exposes {
    hide: () => void;
  }

  type IRowData = ClusterModel<T>;

  defineProps<Props<T>>();

  defineSlots<Slots<T>>();

  const route = useRoute();

  const operationMenuRef = ref<InstanceType<typeof OperationMenu>>();
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

  defineExpose<Exposes>({
    hide() {
      operationMenuRef.value?.hide();
    },
  });
</script>
<style lang="less">
  td.cluster-list-operation-column {
    padding: 0 !important;
  }
</style>
