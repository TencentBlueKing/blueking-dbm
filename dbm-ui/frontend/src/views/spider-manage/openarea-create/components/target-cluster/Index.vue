<template>
  <div>
    <RenderTable
      v-slot="slotProps"
      class="mt16"
      :variable-list="variableList"
      @batch-select-cluster="handleShowBatchSelector">
      <RenderDataRow
        v-for="(item, index) in tableData"
        :key="item.rowKey"
        ref="rowRefs"
        :data="item"
        :is-fixed="slotProps.isOverflow"
        :removeable="tableData.length < 2"
        :variable-list="variableList"
        @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
        @remove="handleRemove(index)" />
    </RenderTable>
    <ClusterSelector
      v-model:is-show="isShowBatchSelector"
      :get-resource-list="getList"
      :selected="selectedClusters"
      :tab-list="clusterSelectorTabList"
      @change="handelClusterChange" />
  </div>
</template>
<script setup lang="ts">
  import { shallowRef } from 'vue';

  import SpiderModel from '@services/model/spider/spider';
  import { getList } from '@services/source/resourceSpider';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector-new/Index.vue';

  import RenderTable from './components/RenderTable.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/Row.vue';

  interface Props {
    variableList: string[]
  }
  interface Exposes{
    getValue: () => Promise<Record<string, any>[]>
  }

  defineProps<Props>();

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData;
  };

  const rowRefs = ref<InstanceType<typeof RenderDataRow>[]>([]);
  const isShowBatchSelector = ref(false);
  const selectedClusters = shallowRef<{[key: string]: Array<SpiderModel>}>({
    [ClusterTypes.TENDBCLUSTER]: [],
  });

  const clusterSelectorTabList = [{
    id: ClusterTypes.TENDBCLUSTER,
    name: '集群',
  }];
  const tableData = shallowRef<IDataRow[]>([createRowData()]);

  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  // 批量选择
  const handelClusterChange = (selected: {[key: string]: Array<SpiderModel>}) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.TENDBCLUSTER];
    const newList = list.reduce((result, item) => {
      const row = createRowData({
        clusterData: {
          id: item.id,
          master_domain: item.master_domain,
          bk_biz_id: item.bk_biz_id,
          bk_cloud_id: item.bk_cloud_id,
          bk_cloud_name: item.bk_cloud_name,
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

  defineExpose<Exposes>({
    getValue() {
      return Promise.all(rowRefs.value.map(item => item.getValue()));
    },
  });
</script>

