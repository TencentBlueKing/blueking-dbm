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
      :show-ip-cloumn="showIpCloumn"
      :variable-list="variableList"
      @batch-edit="handleBatchEdit"
      @batch-ip-selecter="handleShowBatchIpSeletor"
      @batch-select-cluster="handleShowBatchSelector">
      <RenderDataRow
        v-for="(item, index) in tableData"
        :key="item.rowKey"
        ref="rowRefs"
        :data="item"
        :removeable="tableData.length < 2"
        :show-ip-cloumn="showIpCloumn"
        :variable-list="variableList"
        @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
        @clone="(payload: IDataRow) => handleClone(index, payload)"
        @cluster-input-finish="(value) => handleInputCluster(index, value)"
        @remove="handleRemove(index)" />
    </RenderTable>
    <BatchInput
      v-model="isShowBatchInput"
      :variable-list="variableList"
      @change="handleBatchInput" />
    <ClusterSelector
      v-model:is-show="isShowBatchSelector"
      :cluster-types="[ClusterTypes.TENDBCLUSTER]"
      :selected="selectedClusters"
      @change="handelClusterChange" />
    <IpSelector
      v-model:show-dialog="isShowBatchIpSelector"
      :biz-id="currentBizId"
      button-text=""
      :data="localHostList"
      :os-types="[OSTypes.Linux]"
      :panel-list="['staticTopo', 'dbmWhitelist', 'manualInput']"
      service-mode="all"
      :show-view="false"
      @change="handleHostChange"
      @change-whitelist="handleWhitelistChange" />
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { HostInfo } from '@services/types';

  import { ClusterTypes, OSTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import IpSelector, { type IPSelectorResult } from '@components/ip-selector/IpSelector.vue';

  import BatchInput from './components/BatchInput.vue';
  import RenderTable from './components/RenderTable.vue';
  import RenderDataRow, { createRowData, type IData, type IDataRow } from './components/Row.vue';

  interface Props {
    variableList: string[];
    showIpCloumn: boolean;
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
  const isShowBatchIpSelector = ref(false);
  const isShowBatchInput = ref(false);
  const tableData = ref<IDataRow[]>([createRowData()]);

  const localHostList = shallowRef<HostInfo[]>([]);
  const selectedClusters = shallowRef<{ [key: string]: Array<TendbClusterModel> }>({
    [ClusterTypes.TENDBCLUSTER]: [],
  });

  const currentBizId = window.PROJECT_CONFIG.BIZ_ID;

  // 集群域名是否已存在表格的映射表
  const domainMemo: Record<string, boolean> = {};

  const handleHostChange = (hostList: HostInfo[]) => {
    if (checkListEmpty(tableData.value)) {
      return;
    }

    localHostList.value = hostList;
    tableData.value.forEach((item) => (item.authorizeIps = hostList.map((info) => info.ip)));
  };

  const handleWhitelistChange = (whiteList: IPSelectorResult['dbm_whitelist']) => {
    if (checkListEmpty(tableData.value)) {
      return;
    }

    const localIps = localHostList.value.map((item) => item.ip);
    const whiteIps = _.flatMap(whiteList.map((item) => item.ips));
    const finalIps = Array.from(new Set([...localIps, ...whiteIps]));
    localHostList.value = finalIps.map((ip) => ({ ip }) as HostInfo);
    tableData.value.forEach((item) => (item.authorizeIps = localHostList.value.map((info) => info.ip)));
  };

  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  const handleShowBatchIpSeletor = () => {
    isShowBatchIpSelector.value = true;
  };

  // 批量输入
  const handleBatchInput = (rowInfos: IData[]) => {
    tableData.value = rowInfos.map((item) => createRowData(item));
  };

  const handleBatchEdit = (varName: string, list: string[]) => {
    list.forEach((value, index) => {
      if (tableData.value[index]) {
        tableData.value[index].vars[varName] = value;
        return;
      }
      tableData.value[index] = createRowData({
        vars: {
          [varName]: value,
        },
      });
    });
  };

  // 输入集群后查询集群信息并填充到table
  const handleInputCluster = async (index: number, item: TendbClusterModel) => {
    const row = createRowData({
      clusterData: {
        id: item.id,
        master_domain: item.master_domain,
        bk_biz_id: item.bk_biz_id,
        bk_cloud_id: item.bk_cloud_id,
        bk_cloud_name: item.bk_cloud_name,
      },
    });
    tableData.value[index] = row;
    domainMemo[item.master_domain] = true;
    selectedClusters.value[ClusterTypes.TENDBCLUSTER].push(item);
  };

  // 批量选择
  const handelClusterChange = (selected: { [key: string]: Array<TendbClusterModel> }) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.TENDBCLUSTER];
    const newList = list.reduce((result, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = createRowData({
          clusterData: {
            id: item.id,
            master_domain: domain,
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
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  // 复制行数据
  const handleClone = (index: number, sourceData: IDataRow) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, sourceData);
    tableData.value = dataList;
    setTimeout(() => {
      rowRefs.value[rowRefs.value.length - 1].getValue();
    });
  };

  defineExpose<Exposes>({
    getValue() {
      return Promise.all(rowRefs.value.map((item) => item.getValue()));
    },
  });
</script>
