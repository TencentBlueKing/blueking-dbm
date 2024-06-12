<template>
  <div>
    <BkButton
      class="db-clear-batch"
      @click="() => (isShowBatchInput = true)">
      <DbIcon type="add" />
      {{ t('批量录入') }}
    </BkButton>
    <RenderTable
      class="mt16"
      :variable-list="variableList"
      @batch-edit="handleBatchEdit"
      @batch-select-cluster="handleShowBatchSelector">
      <RenderDataRow
        v-for="(item, index) in tableData"
        :key="item.rowKey"
        ref="rowRefs"
        :data="item"
        :removeable="tableData.length < 2"
        :variable-list="variableList"
        @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
        @remove="handleRemove(index)" />
    </RenderTable>
    <BatchInput
      v-model="isShowBatchInput"
      :variable-list="variableList"
      @change="handleBatchInput" />
    <ClusterSelector
      v-model:is-show="isShowBatchSelector"
      :cluster-types="[clusterType]"
      :selected="selectedClusters"
      @change="handelClusterChange" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  import BatchInput from './components/BatchInput.vue';
  import RenderTable from './components/RenderTable.vue';
  import RenderDataRow, { createRowData, type IData, type IDataRow } from './components/Row.vue';

  interface Props {
    clusterType: ClusterTypes;
    variableList: string[];
  }
  interface Exposes {
    getValue: () => Promise<Record<string, any>[]>;
  }

  defineProps<Props>();

  const { t } = useI18n();

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
  const isShowBatchInput = ref(false);

  const selectedClusters = shallowRef<{ [key: string]: Array<TendbhaModel> }>({
    [ClusterTypes.TENDBHA]: [],
    [ClusterTypes.TENDBSINGLE]: [],
  });

  const tableData = ref<IDataRow[]>([createRowData()]);

  // 集群域名是否已存在表格的映射表
  const domainMemo: Record<string, boolean> = {};

  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  const handleBatchEdit = (varName: string, list: string[]) => {
    list.forEach((value, index) => {
      if (tableData.value[index]) {
        tableData.value[index].vars = {
          [varName]: value,
        };
        return;
      }
      tableData.value[index] = createRowData({
        vars: {
          [varName]: value,
        },
      });
    });
  };

  // 批量输入
  const handleBatchInput = (rowInfos: IData[]) => {
    tableData.value = rowInfos.map((item) => createRowData(item));
  };

  // 批量选择
  const handelClusterChange = (selected: { [key: string]: Array<TendbhaModel> }) => {
    selectedClusters.value = selected;
    const list = Object.keys(selected).reduce((list: TendbhaModel[], key) => list.concat(...selected[key]), []);
    const newList = list.reduce((result, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
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
        domainMemo[domain] = true;
      }
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
    const domain = dataList[index].clusterData?.master_domain;
    if (domain) {
      delete domainMemo[domain];
      const clustersArr = selectedClusters.value[ClusterTypes.TENDBHA];
      selectedClusters.value[ClusterTypes.TENDBHA] = clustersArr.filter((item) => item.master_domain !== domain);
    }
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all(rowRefs.value.map((item) => item.getValue()));
    },
  });
</script>
