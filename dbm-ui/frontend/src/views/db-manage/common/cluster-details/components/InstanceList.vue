<template>
  <div class="cluster-detail-instance-list-box">
    <div class="action-box mb-16">
      <InstanceBatchCopy
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
        :title="t('实例')">
        <template #default="{ row }: { row: IColumnData }">
          {{ row.instance_address || '--' }}
          <BkTag
            v-if="standBdyTagMap[row.instance_address]"
            class="cluster-specific-flag ml-4"
            size="small">
            Standby
          </BkTag>
          <BkTag
            v-if="primaryTagMap[row.instance_address]"
            class="cluster-specific-flag ml-4"
            size="small">
            Primary
          </BkTag>
        </template>
      </TableColumn>
      <InstanceListFieldColumn
        :cluster-id="clusterId"
        :cluster-type="clusterType" />
    </DbTable>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRoute, useRouter } from 'vue-router';

  import type { ClusterListNode } from '@services/types';

  import { useInstanceQuickSearch, useUrlSearch } from '@hooks';

  import DbTable from '@components/db-table/IndexNew.vue';

  import InstanceBatchCopy from '@views/db-manage/common/instance-batch-copy/Index.vue';
  import useClusterInstanceList from '@views/db-manage/hooks/useClusterInstaceList';
  import useClusterTableSelect from '@views/db-manage/hooks/useClusterTableSelect';

  import { URL_INSTANCE_MEMO_KEY } from '../constants';
  import InstanceListFieldColumn from '../InstanceListFieldColumn.vue';

  interface Props {
    clusterId: number;
    clusterRoleNodeGroup: Record<
      string,
      ({
        displayInstance?: string;
        isPrimary?: boolean;
        isStandBy?: boolean;
      } & ClusterListNode)[]
    >;
    clusterType: Parameters<typeof useClusterInstanceList>[0];
  }

  type IColumnData = ServiceReturnType<ReturnType<typeof useClusterInstanceList>>['results'][number];

  const props = defineProps<Props>();

  const { t } = useI18n();
  const route = useRoute();
  const router = useRouter();
  const { getSearchParams } = useUrlSearch();

  const requestHandler = useClusterInstanceList(props.clusterType);
  const { handleSelection, selectedList } = useClusterTableSelect<IColumnData>();
  const { quickSearchData, quickSearchValue } = useInstanceQuickSearch({
    cluster_id: props.clusterId,
    cluster_type: props.clusterType,
  });

  const dataSource = (params: ServiceParameters<typeof requestHandler>) =>
    requestHandler({
      ...params,
      cluster_id: props.clusterId,
    });

  const instanceTableRef = useTemplateRef('instanceTable');

  const primaryTagMap = shallowRef<Record<string, boolean>>({});
  const standBdyTagMap = shallowRef<Record<string, boolean>>({});

  watch(
    () => props.clusterRoleNodeGroup,
    () => {
      const latestPrimaryTagMap: Record<string, boolean> = {};
      const latestStandBdyTagMap: Record<string, boolean> = {};
      Object.entries(props.clusterRoleNodeGroup).forEach(([, nodes]) => {
        nodes.forEach((node) => {
          if (node.isPrimary) {
            latestPrimaryTagMap[node.instance] = true;
          }
          if (node.isStandBy) {
            latestStandBdyTagMap[node.instance] = true;
          }
        });
      });
      primaryTagMap.value = latestPrimaryTagMap;
      standBdyTagMap.value = latestStandBdyTagMap;
    },
    {
      immediate: true,
    },
  );

  const getBatchCopyData = () => {
    return instanceTableRef.value!.fetchAllData<IColumnData>();
  };

  const fetchData = () => {
    instanceTableRef.value?.fetchData(quickSearchValue.value);
    // instanceTableRef.value?.clearSelected();
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

  onMounted(() => {
    quickSearchValue.value = JSON.parse(decodeURIComponent(String(route.query[URL_INSTANCE_MEMO_KEY] || '{}')));
    fetchData();
  });
</script>
<style lang="less">
  .cluster-detail-instance-list-box {
    height: 100%;
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
