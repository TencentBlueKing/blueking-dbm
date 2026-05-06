<template>
  <TableColumn
    class-name="instance-list-operation-column"
    col-key="row-operation"
    fixed="left"
    :resizable="false"
    title=" "
    :width="30">
    <template #default="{ row, rowIndex }: { row: IRowData; rowIndex: number }">
      <OperationMenu
        ref="operationMenuRef"
        :style="{
          display: !currentInstanceId ? (rowIndex === 0 ? 'flex' : '') : currentInstanceId === row.id ? 'flex' : '',
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
  import type { InstanceModel, ISupportClusterType } from './types';

  export interface Props<T extends ISupportClusterType> {
    // eslint-disable-next-line vue/no-unused-properties
    clusterType: T;
  }

  export interface Slots<T extends ISupportClusterType> {
    default: (params: { data: InstanceModel<T> }) => void;
  }

  export interface Exposes {
    hide: () => void;
  }

  type IRowData = InstanceModel<T>;

  defineProps<Props<T>>();

  defineSlots<Slots<T>>();

  const route = useRoute();

  const operationMenuRef = ref<InstanceType<typeof OperationMenu>>();
  const currentInstanceId = ref(0);

  watch(
    route,
    () => {
      const currentInstanceIdFromRoute = Number(route.params.instanceId);

      if (currentInstanceIdFromRoute > 0) {
        currentInstanceId.value = currentInstanceIdFromRoute;
      }
    },
    {
      immediate: true,
    },
  );

  const handleShow = (data: IRowData) => {
    currentInstanceId.value = data.id;
  };

  onBeforeUnmount(() => {
    currentInstanceId.value = 0;
  });

  defineExpose<Exposes>({
    hide() {
      operationMenuRef.value?.hide();
    },
  });
</script>
<style lang="less">
  td.instance-list-operation-column {
    padding: 0 !important;
  }
</style>
