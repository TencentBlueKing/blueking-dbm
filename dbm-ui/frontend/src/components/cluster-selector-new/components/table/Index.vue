<template>
  <div class="cluster-selector-table">
    <DbQuickSearch
      v-model="searchValue"
      class="mt-16 mb-16"
      :data="quickSearchData"
      :placeholder="t('请输入或选择条件搜索')"
      @change="handleQuickSearchChange" />
    <DbTable
      ref="clusterTable"
      class="db-cluster-table"
      :container-height="containerHeight"
      :data-source="realDataSource"
      :disable-select-method="realDisableSelectMethod"
      :filter-value="searchValue"
      row-key="id"
      :select-single="single"
      selectable
      :selected="selected"
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <TableColumn
        col-key="master_domain"
        fixed="left"
        :min-width="300"
        :title="t('访问入口')">
        <template #default="{ row }: { row: IRowData }">
          <TextOverflowLayout>
            {{ row.master_domain || '--' }}
            <template #append>
              <BkPopover
                v-if="row.operations && row.operations.length > 0"
                theme="light"
                width="360">
                <BkTag
                  class="operations-length-tag ml-4"
                  theme="info">
                  {{ row.operations.length }}
                </BkTag>
                <template #content>
                  <ClusterRelatedTasks :data="row.operations" />
                </template>
              </BkPopover>
              <BkTag
                v-if="row.isOffline"
                class="ml-4"
                size="small">
                {{ t('已禁用') }}
              </BkTag>
            </template>
          </TextOverflowLayout>
        </template>
      </TableColumn>
      <TableColumn
        col-key="cluster_ids"
        :filter="columnFilter?.['cluster_ids']"
        title="ID"
        :width="80">
        <template #default="{ row }: { row: IRowData }">
          {{ row.id }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="name"
        :filter="columnFilter?.['name']"
        :min-width="250"
        :title="t('集群别名')">
        <template #default="{ row }: { row: IRowData }">
          {{ row.cluster_alias || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="tag"
        :filter="columnFilter?.['tag']"
        :title="t('标签')"
        :width="150">
        <template #default="{ row }: { row: IRowData }">
          <ClusterTag
            :data="row"
            :editable="false"
            mode="vertical" />
        </template>
      </TableColumn>
      <TableColumn
        col-key="status"
        :filter="columnFilter?.['status']"
        :title="t('状态')"
        width="100">
        <template #default="{ row }: { row: IRowData }">
          <ClusterRoleStatus :data="row" />
        </template>
      </TableColumn>
      <InstanceColumn :cluster-type="clusterType" />
      <TableColumn
        v-if="showModuleColumn"
        col-key="db_module_id"
        :filter="columnFilter?.['db_module_id']"
        :title="t('模块')"
        :width="150">
        <template #default="{ row }: { row: IRowData }">
          {{ row.db_module_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        v-if="clusterType === ClusterTypes.REDIS"
        col-key="redis_cluster_type"
        :filter="columnFilter?.['redis_cluster_type']"
        :min-width="150"
        :title="t('架构类型')">
        <template #default="{ row }: { row: RedisModel }">
          {{ row.cluster_type_name || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="major_version"
        :filter="columnFilter?.['major_version']"
        :min-width="150"
        :title="t('版本')">
        <template #default="{ row }: { row: IRowData }">
          {{ row.major_version || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="disaster_tolerance_level"
        :filter="columnFilter?.['disaster_tolerance_level']"
        :min-width="160"
        :title="t('容灾要求')">
        <template #default="{ row }: { row: IRowData }">
          {{ row.disasterToleranceLevelName || '--' }}
        </template>
      </TableColumn>
      <TableColumn
        col-key="region"
        :filter="columnFilter?.['region']"
        :min-width="150"
        :title="t('地域园区')">
        <template #default="{ row }: { row: IRowData }">
          <div>{{ row.regionDisplay }}</div>
          <TextOverflowLayout>{{ row.clusterSubzonesDisplay }}</TextOverflowLayout>
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>

<script setup lang="ts" generic="T extends ISupportClusterType">
  import { useI18n } from 'vue-i18n';

  import RedisModel from '@services/model/redis/redis';

  import { useClusterColumnFilter, useClusterQuickSearch } from '@hooks';

  import { ClusterTypes } from '@common/const';

  import ClusterTag from '@components/cluster-tag/index.vue';
  import DbTable from '@components/db-table/IndexNew.vue';
  import TextOverflowLayout from '@components/text-overflow-layout/Index.vue';

  import ClusterRoleStatus from '@views/db-manage/common/cluster-role-status/Index.vue';
  import useClusterList from '@views/db-manage/hooks/useClusterList';

  import type { ClusterModel, ISupportClusterType } from '../../types';

  import InstanceColumn from './components/InstanceColumn.vue';
  import ClusterRelatedTasks from './components/task-panel/Index.vue';

  export interface Props<C extends ISupportClusterType> {
    clusterType: ISupportClusterType;
    dataSourceMap?: {
      [key in C]?: ReturnType<typeof useClusterList<key>>;
    };
    disableSelectMethod?: (data: ClusterModel<C>) => boolean | string;
    selected: ClusterModel<C>[];
    single?: boolean;
    supportOfflineData?: boolean;
  }

  type Emits = (e: 'selection', list: IRowData[]) => void;

  type IRowData = ClusterModel<T>;

  const props = defineProps<Props<T>>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const requestHandler = useClusterList(props.clusterType);

  const clusterMap: { [x in ISupportClusterType]?: ClusterTypes | ClusterTypes[] } = {
    [ClusterTypes.REDIS]: [
      ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
      ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
      ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
      ClusterTypes.PREDIXY_REDIS_CLUSTER,
    ],
  };

  const quickSearchClusterType = clusterMap[props.clusterType] || props.clusterType;
  const { quickSearchData, searchValue } = useClusterQuickSearch(quickSearchClusterType);

  const { data: columnFilter } = useClusterColumnFilter({
    cluster_attrs: ['db_module_id', 'major_version', 'region', 'disaster_tolerance_level'] as const,
    cluster_type: props.clusterType,
  });

  const showModuleColumn = [
    ClusterTypes.RIAK,
    ClusterTypes.SQLSERVER_HA,
    ClusterTypes.SQLSERVER_SINGLE,
    ClusterTypes.TENDBCLUSTER,
    ClusterTypes.TENDBHA,
    ClusterTypes.TENDBSINGLE,
  ].includes(props.clusterType);

  const containerHeight = 570 - 32 - 16; // 去除搜索框的高度和margin bottom

  const clusterTableRef = useTemplateRef('clusterTable');

  const realDisableSelectMethod = (data: ClusterModel<T>) => {
    if (!props.supportOfflineData && data.isOffline) {
      return t('集群已禁用');
    }
    if (props.disableSelectMethod) {
      return props.disableSelectMethod(data);
    }
    return false;
  };

  const realDataSource = (params: any) => {
    let paramsClusterType = '';
    if (
      [ClusterTypes.MONGO_REPLICA_SET, ClusterTypes.MONGO_SHARED_CLUSTER, ClusterTypes.REDIS_INSTANCE].includes(
        props.clusterType,
      )
    ) {
      paramsClusterType = props.clusterType;
    }
    if (props.clusterType === ClusterTypes.REDIS) {
      paramsClusterType = (clusterMap[props.clusterType] as ClusterTypes[]).join(',');
    }
    return (props.dataSourceMap?.[props.clusterType as T] || requestHandler)({
      ...params,
      cluster_type: paramsClusterType || undefined,
    });
  };

  const fetchData = () => {
    clusterTableRef.value!.fetchData(Object.assign({}, searchValue.value));
  };

  const handleQuickSearchChange = () => {
    fetchData();
  };

  const handleFilterChange = (filterValue: Record<string, string>) => {
    searchValue.value = filterValue;
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
  .cluster-selector-table {
    height: 570px;
    padding: 0 24px;

    .db-cluster-table {
      .operations-length-tag {
        height: 16px;
        color: #3a84ff;
        border-radius: 8px !important;
      }
    }
  }
</style>
