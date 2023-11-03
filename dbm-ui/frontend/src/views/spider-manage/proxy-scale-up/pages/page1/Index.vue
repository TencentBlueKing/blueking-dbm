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
        :title="$t('扩容接入层：增加集群的Proxy数量')" />
      <RenderData
        v-slot="slotProps"
        class="mt16"
        @show-batch-selector="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :choosed-node-type="clusterNodeTypeMap[item.cluster]"
          :data="item"
          :is-fixed="slotProps.isOverflow"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @node-type-choosed="(label: string) => handleChangeNodeType(index, item.cluster, label)"
          @remove="handleRemove(index, item.cluster)" />
      </RenderData>
      <ClusterSelector
        v-model:is-show="isShowMasterInstanceSelector"
        :get-resource-list="getList"
        :selected="selectedClusters"
        :show-preview-result-title="false"
        :tab-list="clusterSelectorTabList"
        @change="handelClusterChoosed" />
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :disabled="!canSubmit"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ $t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="$t('重置将会情况当前填写的所有内容_请谨慎操作')"
        :title="$t('确认重置页面')">
        <BkButton
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ $t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import SpiderModel from '@services/model/spider/spider';
  import { getList } from '@services/spider';
  import { createTicket } from '@services/ticket';
  import type { SubmitTicket } from '@services/types/ticket';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    TicketTypes,
  } from '@common/const';

  import ClusterSelector from '@components/cluster-selector-new/Index.vue';

  import { random } from '@utils';

  import SpiderTable from './components/cluster-selector-table/Index.vue';
  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
    type InfoItem,
  } from './components/Row.vue';

  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();
  const router = useRouter();

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting  = ref(false);
  const tableData = ref([createRowData()]);
  const clusterNodeTypeMap = ref<Record<string, string[]>>({});

  const selectedClusters = shallowRef<{[key: string]: Array<SpiderModel>}>({ [ClusterTypes.TENDBCLUSTER]: [] });

  const totalNum = computed(() => (tableData.value.length > 0
    ? new Set(tableData.value.map(item => item.cluster)).size : 0));
  const canSubmit = computed(() => tableData.value.filter(item => Boolean(item.cluster)).length > 0);

  const clusterSelectorTabList = [{
    id: ClusterTypes.TENDBCLUSTER as string,
    name: t('集群选择'),
    content: SpiderTable as unknown as Element,
  }];

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  const handleChangeNodeType = (index: number, domain: string, label: string) => {
    tableData.value[index].nodeType = label;
    const domainCount = tableData.value.filter(item => item.cluster === domain).length;
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
  const generateRowDateFromRequest = (item: SpiderModel) => {
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
      spec: {
        ...item.cluster_spec,
        name: item.cluster_spec.spec_name,
        id: item.cluster_spec.spec_id,
        count: 0,
      },
      targetNum: '',
    };
  };

  // 批量选择
  const handelClusterChoosed = async (selected: {[key: string]: Array<SpiderModel>}) => {
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
    if (tableData.value[index].cluster === domain) return;
    tableData.value[index].isLoading = true;
    const ret = await getList({ domain }).finally(() => {
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
      const index = sameClusterArr.findIndex(item => item === nodeType);
      if (index > -1) {
        sameClusterArr.splice(index, 1);
      }
    }
    tableData.value.splice(index, 1);
    const clustersArr = selectedClusters.value[ClusterTypes.TENDBCLUSTER];
    selectedClusters.value[ClusterTypes.TENDBCLUSTER] = clustersArr.filter(item => item.master_domain !== cluster);
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const infos = await Promise.all<InfoItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<InfoItem>
    }) => item.getValue()));

    const params: SubmitTicket<TicketTypes, InfoItem[]> & { remark: string} = {
      remark: '',
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.TENDBCLUSTER_SPIDER_ADD_NODES,
      details: {
        ip_source: 'resource_pool',
        infos,
      },
    };

    InfoBox({
      title: t('确认对n个集群扩容接入层？', { n: totalNum.value }),
      width: 480,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
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
        })
          .catch((e) => {
            console.error('submit spider scale up ticket error：', e);
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

  const handleReset = () => {
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

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;

      .safe-action {
        margin-left: auto;

        .safe-action-text {
          padding-bottom: 2px;
          border-bottom: 1px dashed #979ba5;
        }
      }
    }
  }

  .bottom-btn {
    width: 88px;
  }
</style>
