<template>
  <div class="instance-selector-table">
    <DbQuickSearch
      v-model="quickSearchValue"
      class="mt-16 mb-16"
      :data="quickSearchData"
      :placeholder="t('请输入或选择条件搜索')"
      @change="handleQuickSearchChange" />
    <DbTable
      ref="instanceTable"
      class="db-instance-table"
      :container-height="570 - 32 - 16"
      :data-source="requestHandler"
      :disable-select-method="disableSelectMethod"
      :filter-value="quickSearchValue"
      row-key="instance_address"
      :select-single="selectSingle"
      selectable
      :selected="selected"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <TableColumn
        col-key="instance_address"
        fixed="left"
        :min-width="250"
        :title="t('实例')">
        <template #default="{ row }: { row: InstanceModel }">
          {{ row.instance_address || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="status"
        :filter="columnFilter?.['status']"
        :title="t('状态')"
        width="100">
        <template #default="{ row }: { row: InstanceModel }">
          <ClusterInstanceStatus :data="row.status" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="role"
        :filter="columnFilter?.['role']"
        :title="t('部署角色')"
        :width="140">
        <template #default="{ row }: { row: InstanceModel }">
          {{ row.role }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="version"
        :filter="columnFilter?.['version']"
        :title="t('版本')"
        :width="140">
        <template #default="{ row }: { row: InstanceModel }">
          {{ row.version || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="related_clusters"
        :title="t('关联集群')">
        <template #default="{ row }: { row: InstanceModel }">
          {{ row.master_domain || '--' }}
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import { useInstanceColumnFilter, useInstanceQuickSearch } from '@hooks';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import type { InstanceModel, ISupportClusterType } from '../types';

  import useInstaceList from './useInstaceList';

  interface Props {
    clusterType: ISupportClusterType;
    disableSelectMethod?: (data: InstanceModel) => boolean | string;
    selected: InstanceModel[];
    selectSingle?: boolean;
    sourceDataParams?: { [key in ISupportClusterType]?: Record<string, any> };
  }

  type Emits = (e: 'selection', list: InstanceModel[]) => void;

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const requestHandler = useInstaceList(props.clusterType);

  const { quickSearchData, quickSearchValue } = useInstanceQuickSearch({ cluster_type: props.clusterType });
  const { data: columnFilter } = useInstanceColumnFilter({
    cluster_type: props.clusterType,
    instance_attrs: ['role', 'version', 'bk_os_name', 'bk_sub_zone'] as const,
  });

  const instanceTableRef = useTemplateRef('instanceTable');

  const fetchData = () => {
    instanceTableRef.value!.fetchData(
      Object.assign(
        {},
        quickSearchValue.value,
        props.sourceDataParams ? props.sourceDataParams[props.clusterType] || {} : {},
      ),
    );
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
    fetchData();
  };

  const handleSelection = (_key: string[], list: InstanceModel[]) => {
    emits('selection', list);
  };

  onMounted(() => {
    fetchData();
  });
</script>

<style lang="less">
  .instance-selector-table {
    height: 570px;
    padding: 0 24px;
  }
</style>
