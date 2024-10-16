<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <SmartAction>
    <div class="proxy-scale-up-page">
      <BkAlert
        closable
        theme="info"
        :title="t('扩容接入层：增加集群的Proxy数量')" />
      <RenderData
        class="mt16"
        @show-batch-selector="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :choosed-node-type="clusterNodeTypeMap[item.cluster]"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @clone="(payload: IDataRow) => handleClone(index, payload)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @node-type-choosed="(label: string) => handleChangeNodeType(index, item.cluster, label)"
          @remove="handleRemove(index, item.cluster)" />
      </RenderData>
      <TicketRemark v-model="remark" />
      <ClusterSelector
        v-model:is-show="isShowMasterInstanceSelector"
        :cluster-types="[ClusterTypes.TENDBCLUSTER]"
        :selected="selectedClusters"
        support-offline-data
        :tab-list-config="tabListConfig"
        @change="handelClusterChoosed" />
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :disabled="!canSubmit"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TendbClusterModel from '@services/model/tendbcluster/tendbcluster';
  import { getTendbClusterList } from '@services/source/tendbcluster';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import { random } from '@utils';

  import RenderData from './components/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow, type InfoItem } from './components/Row.vue';

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES,
    onSuccess(cloneData) {
      tableData.value = cloneData.tableDataList;
      remark.value = cloneData.remark;
      window.changeConfirm = true;
    },
  });

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting = ref(false);
  const tableData = ref([createRowData()]);
  const clusterNodeTypeMap = ref<Record<string, string[]>>({});
  const remark = ref('');

  const selectedClusters = shallowRef<{ [key: string]: Array<TendbClusterModel> }>({ [ClusterTypes.TENDBCLUSTER]: [] });

  const canSubmit = computed(() => tableData.value.filter((item) => Boolean(item.cluster)).length > 0);

  const tabListConfig = {
    [ClusterTypes.TENDBCLUSTER]: {
      disabledRowConfig: [
        {
          handler: (data: TendbClusterModel) => data.status !== 'normal',
          tip: t('集群异常'),
        },
      ],
    },
  };

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  const handleChangeNodeType = (index: number, domain: string, label: string) => {
    tableData.value[index].nodeType = label;
    const domainCount = tableData.value.filter((item) => item.cluster === domain).length;
    const sameDomainArr = clusterNodeTypeMap.value[domain];
    if (sameDomainArr === undefined) {
      clusterNodeTypeMap.value[domain] = [label];
    } else {
      if (domainCount === 1) {
        clusterNodeTypeMap.value[domain] = [label];
        return;
      }
      if (sameDomainArr.length < 2) {
        sameDomainArr.push(label);
      }
    }
  };

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.cluster;
  };

  // Master 批量选择
  const handleShowBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };

  // 根据集群选择返回的数据加工成table所需的数据
  const generateRowDateFromRequest = (item: TendbClusterModel) => {
    const masterCount = item.spider_master.length;
    const slaveCount = item.spider_slave.length;
    return {
      rowKey: random(),
      isLoading: false,
      cluster: item.master_domain,
      clusterId: item.id,
      bkCloudId: item.bk_cloud_id,
      clusterType: item.cluster_spec.spec_cluster_type,
      nodeType: '',
      masterCount,
      slaveCount,
      mntCount: item.spider_mnt.length,
      // spec: {
      // ...item.spider_master[0].spec_config,
      // count: 0,
      // },
      specId: item.spider_master[0].spec_config.id,
      targetNum: '',
      spiderMasterList: item.spider_master,
      spiderSlaveList: item.spider_slave,
    };
  };

  // 批量选择
  const handelClusterChoosed = async (selected: { [key: string]: Array<TendbClusterModel> }) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.TENDBCLUSTER];
    const newList = list.reduce((result, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = generateRowDateFromRequest(item);
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

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, domain: string) => {
    if (!domain) {
      const { cluster } = tableData.value[index];
      domainMemo[cluster] = false;
      tableData.value[index].cluster = '';
      return;
    }

    if (tableData.value[index].cluster === domain) {
      return;
    }
    tableData.value[index].isLoading = true;
    const ret = await getTendbClusterList({ domain }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (ret.results.length < 1) {
      return;
    }
    const data = ret.results[0];
    const row = generateRowDateFromRequest(data);
    tableData.value[index] = row;
    domainMemo[domain] = true;
    selectedClusters.value[ClusterTypes.TENDBCLUSTER].push(data);
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };
  // 删除一个集群
  const handleRemove = async (index: number, cluster: string) => {
    if (!cluster) {
      tableData.value.splice(index, 1);
      return;
    }
    delete domainMemo[cluster];
    const { nodeType } = tableData.value[index];
    // 恢复已选择的节点类型到列表
    const sameClusterArr = clusterNodeTypeMap.value[cluster];
    if (sameClusterArr && nodeType) {
      const index = sameClusterArr.findIndex((item) => item === nodeType);
      if (index > -1) {
        sameClusterArr.splice(index, 1);
      }
    }
    tableData.value.splice(index, 1);
    const clustersArr = selectedClusters.value[ClusterTypes.TENDBCLUSTER];
    selectedClusters.value[ClusterTypes.TENDBCLUSTER] = clustersArr.filter((item) => item.master_domain !== cluster);
  };

  // 复制行数据
  const handleClone = (index: number, sourceData: IDataRow) => {
    const dataList = [...tableData.value];
    const rowData = _.cloneDeep(dataList[index]);
    dataList.splice(
      index + 1,
      0,
      Object.assign(sourceData, {
        clusterId: rowData.clusterId,
        bkCloudId: rowData.bkCloudId,
        masterCount: rowData.masterCount,
        slaveCount: rowData.slaveCount,
        mntCount: rowData.mntCount,
        spiderMasterList: rowData.spiderMasterList,
        spiderSlaveList: rowData.spiderSlaveList,
        clusterType: rowData.clusterType,
      }),
    );
    tableData.value = dataList;
    setTimeout(() => {
      rowRefs.value[rowRefs.value.length - 1].getValue();
    });
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      const infos = await Promise.all(
        rowRefs.value.map((item: { getValue: () => Promise<InfoItem> }) => item.getValue()),
      );
      const params = {
        remark: remark.value,
        bk_biz_id: currentBizId,
        ticket_type: TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES,
        details: {
          ip_source: 'resource_pool',
          infos,
        },
      };
      await createTicket(params).then((data) => {
        window.changeConfirm = false;
        router.push({
          name: 'SpiderProxyScaleUp',
          params: {
            page: 'success',
          },
          query: {
            ticketId: data.id,
          },
        });
      });
    } finally {
      isSubmitting.value = false;
    }
  };

  const handleReset = () => {
    remark.value = '';
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.TENDBCLUSTER] = [];
    domainMemo = {};
    clusterNodeTypeMap.value = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .proxy-scale-up-page {
    padding-bottom: 20px;
  }

  .bottom-btn {
    width: 88px;
  }
</style>
