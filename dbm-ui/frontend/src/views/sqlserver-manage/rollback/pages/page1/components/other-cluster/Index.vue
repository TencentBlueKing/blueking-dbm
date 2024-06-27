<template>
  <div>
    <RenderData
      class="mt16"
      @batch-select-cluster="handleShowBatchSelector"
      @batch-select-target-cluster="handleShowBatchTargetSelector">
      <RenderDataRow
        v-for="(item, index) in tableData"
        :key="item.rowKey"
        ref="rowRefs"
        :data="item"
        :removeable="tableData.length < 2"
        @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
        @remove="handleRemove(index)" />
    </RenderData>
    <ClusterSelector
      v-model:is-show="isShowBatchSrcSelector"
      :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
      :selected="selectedSrcClusters"
      @change="handelClusterChange" />
    <ClusterSelector
      v-model:is-show="isShowBatchTargetSelector"
      :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
      :selected="selectedTargetClusters"
      :tab-list-config="dstClusterSelectorTabListConfig"
      @change="handelTargetClusterChange" />
  </div>
</template>
<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import SqlServerHaClusterModel from '@services/model/sqlserver/sqlserver-ha-cluster';
  import SqlServerSingleClusterModel from '@services/model/sqlserver/sqlserver-single-cluster';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  import RenderData from './components/RenderData.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/Row.vue';

  const { t } = useI18n();

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData;
  };

  const rowRefs = ref();
  const isShowBatchSrcSelector = ref(false);
  const isShowBatchTargetSelector = ref(false);

  const selectedSrcClusters = shallowRef<{
    [key: string]: (SqlServerSingleClusterModel | SqlServerHaClusterModel)[];
  }>({
    [ClusterTypes.SQLSERVER_HA]: [],
    [ClusterTypes.SQLSERVER_SINGLE]: [],
  });

  const selectedTargetClusters = shallowRef<{
    [key: string]: (SqlServerSingleClusterModel | SqlServerHaClusterModel)[];
  }>({
    [ClusterTypes.SQLSERVER_HA]: [],
    [ClusterTypes.SQLSERVER_SINGLE]: [],
  });

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);

  const dstClusterSelectorTabListConfig = {
    [ClusterTypes.SQLSERVER_HA]: {
      disabledRowConfig: [
        {
          handler: (data: SqlServerSingleClusterModel) =>
            _.flatten(Object.values(selectedSrcClusters.value)).some((item) => item.id === data.id),
          tip: t('待回档集群'),
        },
      ],
    },
    [ClusterTypes.SQLSERVER_SINGLE]: {
      disabledRowConfig: [
        {
          handler: (data: SqlServerSingleClusterModel) =>
            _.flatten(Object.values(selectedSrcClusters.value)).some((item) => item.id === data.id),
          tip: t('待回档集群'),
        },
      ],
    },
  };

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSrcSelector.value = true;
  };

  const handleShowBatchTargetSelector = () => {
    isShowBatchTargetSelector.value = true;
  };

  const handelClusterChange = (selected: {
    [key: string]: Array<SqlServerSingleClusterModel | SqlServerHaClusterModel>;
  }) => {
    selectedSrcClusters.value = selected;
    const list = _.flatten(Object.values(selected));
    const newList = list.reduce((result, item) => {
      const row = createRowData({
        clusterData: {
          id: item.id,
          domain: item.master_domain,
          cloudId: item.bk_cloud_id,
        },
      });
      result.push(row);

      return result;
    }, [] as IDataRow[]);
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  const handelTargetClusterChange = (value: {
    [key: string]: Array<SqlServerSingleClusterModel | SqlServerHaClusterModel>;
  }) => {
    selectedTargetClusters.value = value;
    const lastestTableData = [...tableData.value];
    _.flatten(Object.values(value)).forEach((clusterData, index) => {
      const dstClusterData = {
        id: clusterData.id,
        domain: clusterData.master_domain,
        cloudId: clusterData.bk_cloud_id,
      };
      if (lastestTableData[index]) {
        lastestTableData[index] = {
          ...lastestTableData[index],
          dstClusterData,
        };
      } else {
        lastestTableData.push(
          createRowData({
            dstClusterData,
          }),
        );
      }
    });
    tableData.value = lastestTableData;
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
  };
  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    dataList.splice(index, 1);
    tableData.value = dataList;
  };
</script>
