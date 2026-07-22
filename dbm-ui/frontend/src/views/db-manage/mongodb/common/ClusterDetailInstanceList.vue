<template>
  <div class="cluster-detail-instance-list-box">
    <div class="action-box mb-16">
      <BkButton
        :disabled="selectedList.length < 1"
        style="width: 105px"
        theme="primary"
        @click="handleBatchRestart">
        {{ t('批量重启') }}
      </BkButton>
      <InstanceBatchCopy
        class="ml-8"
        field="instance_address"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <InstanceBatchCopy
        class="ml-8"
        field="ip"
        :get-table-data="getBatchCopyData"
        :selected="selectedList" />
      <DbQuickSearch
        v-model="quickSearchValue"
        :data="quickSearchData"
        :placeholder="t('请输入或选择条件搜索')"
        style="width: 500px; margin-left: auto"
        @change="handleQuickSearchChange" />
    </div>
    <DbTable
      ref="instanceTable"
      :data-source="dataSource"
      :filter-value="quickSearchValue"
      releate-url-query
      row-key="id"
      selectable
      @filter-change="handleFilterChange"
      @selection="handleSelection">
      <TableColumn
        col-key="instance_address"
        fixed="left"
        :min-width="200"
        :title="t('实例')" />
      <TableColumn
        col-key="instance_domain"
        :min-width="300"
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
      <InstanceListFieldColumn
        :cluster-id="clusterId"
        :cluster-type="clusterType" />
      <TableColumn
        col-key="action"
        fixed="right"
        :title="t('操作')"
        :width="60">
        <template #default="{ row }: { row: MongodbInstanceModel }">
          <BkButton
            text
            theme="primary"
            @click="handleSingleRestart(row)">
            {{ t('重启') }}
          </BkButton>
        </template>
      </TableColumn>
    </DbTable>
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import MongodbInstanceModel from '@services/model/mongodb/mongodb-instance';

  import { useInstanceColumnFilter, useInstanceQuickSearch, useUrlSearch } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import DbTable from '@components/db-table/IndexNew.vue';

  import { InstanceListFieldColumn, URL_INSTANCE_MEMO_KEY } from '@views/db-manage/common/cluster-details';
  import InstanceBatchCopy from '@views/db-manage/common/instance-batch-copy/Index.vue';
  import useClusterInstanceList from '@views/db-manage/hooks/useClusterInstaceList';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';

  interface Props {
    clusterId: number;
    clusterType: ClusterTypes.MONGO_REPLICA_SET | ClusterTypes.MONGO_SHARED_CLUSTER;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { getSearchParams } = useUrlSearch();

  const requestHandler = useClusterInstanceList(props.clusterType);
  const { handleSelection, selectedList } = useClusterTableSelect<MongodbInstanceModel>();
  const { quickSearchData, quickSearchValue } = useInstanceQuickSearch({ cluster_type: props.clusterType });
  const { data: columnFilter } = useInstanceColumnFilter({
    cluster_id: props.clusterId,
    cluster_type: props.clusterType,
  });

  const dataSource = (params: ServiceParameters<typeof requestHandler>) =>
    requestHandler({
      ...params,
      cluster_id: props.clusterId,
      cluster_type: props.clusterType,
    });

  const instanceTableRef = useTemplateRef('instanceTable');

  const fetchData = () => {
    instanceTableRef.value?.fetchData(quickSearchValue.value);
    // instanceTableRef.value?.clearSelected();
  };

  const getBatchCopyData = () => {
    return instanceTableRef.value!.fetchAllData<MongodbInstanceModel>();
  };

  const handleQuickSearchChange = _.debounce(() => {
    fetchData();
    router.replace({
      query: {
        ...getSearchParams(),
        [URL_INSTANCE_MEMO_KEY]: encodeURIComponent(JSON.stringify(quickSearchValue.value)),
      },
    });
  }, 100);

  const handleFilterChange = (filterValue: Record<string, string>) => {
    quickSearchValue.value = filterValue;
    fetchData();
  };

  // 跳转到工具箱滚动重启页面，携带已选实例
  const navigateToToolbox = (instances: MongodbInstanceModel[]) => {
    if (instances.length === 0) {
      return;
    }

    const routeInfo = router.resolve({
      name: TicketTypes.MONGODB_INSTANCE_RELOAD,
      query: { instances: instances.map((item) => item.instance_address).join(',') },
    });
    window.open(routeInfo.href, '_blank');
  };

  const handleBatchRestart = () => {
    navigateToToolbox(selectedList.value);
  };

  const handleSingleRestart = (data: MongodbInstanceModel) => {
    navigateToToolbox([data]);
  };

  onMounted(() => {
    quickSearchValue.value = JSON.parse(decodeURIComponent(String(route.query[URL_INSTANCE_MEMO_KEY] || '{}')));
    fetchData();
  });
</script>
<style lang="less">
  .cluster-detail-instance-list-box {
    padding: 18px 0;

    .action-box {
      display: flex;
    }

    .is-show {
      transform: rotateZ(180deg);
      transition: all 0.15s;
    }
  }
</style>
