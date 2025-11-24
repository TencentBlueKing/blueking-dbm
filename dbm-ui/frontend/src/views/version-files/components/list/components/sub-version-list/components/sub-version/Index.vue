<template>
  <CollapseCard class="sub-version-main">
    <template #title>
      <OperationHeader
        ref="operationHeaderRef"
        :data="data"
        :db-version-list-count="dbVersionListCount"
        @add-new-version="() => emits('addNewVersion')"
        @delete-version-series="() => emits('deleteVersionSeries')" />
    </template>
    <TableList
      ref="tableListRef"
      :series-id="data?.id"
      @edit-db-version="(data) => emits('editDbVersion', data)"
      @list-change="handleTableListChange" />
  </CollapseCard>
</template>
<script setup lang="ts">
  import DbVersionModel from '@services/model/version-file/db-version';

  import CollapseCard from '@/components/collapse-card/Index.vue';

  import OperationHeader from './components/OperationHeader.vue';
  import TableList from './components/table-list/Index.vue';

  interface Props {
    data?: {
      distribution: number;
      id: number;
      name: string;
    };
  }

  interface Emits {
    (e: 'addNewVersion'): void;
    (e: 'editDbVersion', version: DbVersionModel): void;
    (e: 'deleteVersionSeries'): void;
  }

  interface Exposes {
    filterSearch: (value: { filter: Record<string, any> }) => void;
    refresh: () => void;
  }

  withDefaults(defineProps<Props>(), {
    data: undefined,
  });
  const emits = defineEmits<Emits>();

  const tableListRef = ref<InstanceType<typeof TableList>>();
  const operationHeaderRef = ref<InstanceType<typeof OperationHeader>>();
  const dbVersionListCount = ref(0);

  const handleTableListChange = (count: number) => {
    dbVersionListCount.value = count;
  };

  defineExpose<Exposes>({
    filterSearch: (value: { filter: Record<string, any> }) => {
      tableListRef.value?.filterSearch(value);
    },
    refresh: () => {
      tableListRef.value?.refresh();
    },
  });
</script>
<style lang="less">
  .sub-version-main {
    width: 100%;
    padding: 0 !important;

    .card-title {
      height: 40px;
      padding-left: 12px;
      overflow: visible;
      background: #f0f1f5;
      border-radius: 2px;
    }

    .card-content {
      margin: 0 !important;
    }
  }
</style>
