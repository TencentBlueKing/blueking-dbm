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
      :container-height="containerHeight"
      :data-source="realDataSource"
      :disable-select-method="disableSelectMethod"
      :filter-value="quickSearchValue"
      row-key="instance_address"
      :select-single="single"
      selectable
      :selected="selected"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <TableColumn
        col-key="instance_address"
        fixed="left"
        :min-width="160"
        :title="t('实例')">
        <template #default="{ row }: { row: IRowData }">
          {{ row.instance_address || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="id"
        :filter="columnFilter?.['id']"
        title="ID"
        :width="80">
        <template #default="{ row }: { row: IRowData }">
          {{ row.id }}
        </template>
      </TableColumn>
      <TableColumn
        v-if="isMongodb"
        col-key="instance_domain"
        :min-width="250"
        :title="t('域名')">
        <template #default="{ row }: { row: MongodbInstanceModel }">
          {{ row.instance_domain || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        v-if="clusterType === ClusterTypes.MONGO_SHARED_CLUSTER"
        col-key="shard"
        :filter="columnFilter?.['shard']"
        :title="t('分片名')"
        :width="150">
        <template #default="{ row }: { row: MongodbInstanceModel }">
          {{ row.shard || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="status"
        :filter="columnFilter?.['status']"
        :title="t('状态')"
        width="100">
        <template #default="{ row }: { row: IRowData }">
          <ClusterInstanceStatus :data="row.status" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="role"
        :filter="columnFilter?.['role']"
        :title="t('部署角色')"
        :width="140">
        <template #default="{ row }: { row: IRowData }">
          {{ row.role }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="version"
        :filter="columnFilter?.['version']"
        :title="t('版本')"
        :width="140">
        <template #default="{ row }: { row: IRowData }">
          {{ row.version || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        :col-key="isMongodb ? 'cluster_name' : 'master_domain'"
        :min-width="250"
        :title="t('关联集群')">
        <template #default="{ row }: { row: IRowData }">
          {{ isMongodb ? row.cluster_name : row.master_domain }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="ip"
        :filter="columnFilter?.['ip']"
        :title="t('主机 IP')"
        :width="140">
      </TableColumn>
      <TableColumn
        col-key="bk_sub_zone"
        :filter="columnFilter?.['bk_sub_zone']"
        :title="t('园区')"
        :width="140">
        <template #default="{ row }: { row: IRowData }">
          {{ row.bk_sub_zone || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="bk_os_name"
        :filter="columnFilter?.['bk_os_name']"
        :title="t('操作系统')"
        :width="140">
        <template #default="{ row }: { row: IRowData }">
          {{ row.bk_os_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="create_at"
        :filter="columnFilter?.['create_at']"
        sorter
        :title="t('部署时间')"
        :width="140">
        <template #default="{ row }: { row: IRowData }">
          {{ row.createAtDisplay || '--' }}
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';

  import { useInstanceColumnFilter, useInstanceQuickSearch } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import ClusterInstanceStatus from '@components/cluster-instance-status/Index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';

  import useClusterInstaceList from '@views/db-manage/hooks/useClusterInstaceList';

  import type { InstanceModel, ISupportClusterType } from '../types';

  export interface Props<C extends ISupportClusterType> {
    clusterType: ISupportClusterType;
    dataSourceMap?: {
      [key in C]?: ReturnType<typeof useClusterInstaceList<key>>;
    };
    disableSelectMethod?: (data: InstanceModel<C>) => boolean | string;
    selected: InstanceModel<C>[];
    single?: boolean;
  }

  type Emits = (e: 'selection', list: IRowData[]) => void;

  type IRowData = InstanceModel<T>;

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const requestHandler = useClusterInstaceList(props.clusterType);

  const { quickSearchData, quickSearchValue } = useInstanceQuickSearch({ cluster_type: props.clusterType });
  const { data: columnFilter } = useInstanceColumnFilter({
    cluster_type: props.clusterType,
    instance_attrs: ['role', 'version', 'bk_os_name', 'bk_sub_zone'] as const,
  });

  const instanceTableRef = useTemplateRef('instanceTable');

  const containerHeight = 570 - 32 - 16; // 去除搜索框的高度和margin bottom
  const isMongodb = [ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER].includes(props.clusterType);

  const realDataSource = (params: any) => (props.dataSourceMap?.[props.clusterType as T] || requestHandler)(params);

  const fetchData = () => {
    instanceTableRef.value!.fetchData(Object.assign({}, quickSearchValue.value));
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
    fetchData();
  };

  const handleSelection = (_key: string[], list: IRowData[]) => {
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
