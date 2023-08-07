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
    <div class="proxy-scale-down-page">
      <BkAlert
        closable
        theme="info"
        :title="$t('缩容接入层：XXX')" />
      <div class="top-opeartion">
        <BkCheckbox
          v-model="isIgnoreBusinessAccess"
          style="padding-top: 6px;">
          {{ $t('忽略业务连接') }}
        </BkCheckbox>
      </div>
      <RenderData
        class="mt16"
        @show-master-batch-selector="handleShowMasterBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :choosed-node-type="clusterNodeTypeMap[item.cluster]"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @node-type-choosed="(label: string) => handleChangeNodeType(item.cluster, label)"
          @remove="handleRemove(index, item.cluster)" />
      </RenderData>
      <ClusterSelector
        v-model:is-show="isShowClusterSelector"
        :tab-list="clusterSelectorTabList"
        @change="handelClusterChange" />
    </div>
    <template #action>
      <BkButton
        class="w-88"
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

<script setup lang="ts">
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

  import ClusterSelector from '@views/spiderss-manage/common/cluster-selector/ClusterSelector.vue';

  import { random } from '@utils';

  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
    type InfoItem,
  } from './components/Row.vue';

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.cluster;
  };

  const router = useRouter();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();
  const rowRefs = ref();
  const isShowClusterSelector = ref(false);
  const isSubmitting  = ref(false);

  const tableData = ref([createRowData()]);
  const isIgnoreBusinessAccess = ref(false);
  const totalNum = computed(() => (tableData.value.length > 0
    ? new Set(tableData.value.map(item => item.cluster)).size : 0));

  const clusterSelectorTabList = [ClusterTypes.SPIDER];
  const clusterNodeTypeMap = ref<Record<string, string[]>>({});

  const handleChangeNodeType = (domain: string, label: string) => {
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

  // Master 批量选择
  const handleShowMasterBatchSelector = () => {
    isShowClusterSelector.value = true;
  };

  // 根据集群选择返回的数据加工成table所需的数据
  const generateRowDateFromRequest = (item: SpiderModel) => ({
    rowKey: random(),
    isLoading: false,
    cluster: item.master_domain,
    clusterId: item.id,
    bkCloudId: item.bk_cloud_id,
    nodeType: '',
    masterCount: item.spider_master.length,
    slaveCount: item.spider_slave.length,
    spec: {
      ...item.cluster_spec,
      name: item.cluster_spec.spec_name,
      id: item.cluster_spec.spec_id,
      count: 0,
    },
    targetNum: '1',
  });

  // 批量选择
  const handelClusterChange = async (selected: {[key: string]: Array<SpiderModel>}) => {
    const list = selected[ClusterTypes.SPIDER];
    const newList = list.reduce((result, item) => {
      const row = generateRowDateFromRequest(item);
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

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, domain: string) => {
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
    const rowInfo = await rowRefs.value[index].getValue()
      .finally(() => {
        tableData.value.splice(index, 1);
      });
    // 恢复已选择的节点类型到列表
    const sameClusterArr = clusterNodeTypeMap.value[cluster];
    if (sameClusterArr) {
      const index = sameClusterArr.findIndex(item => item === rowInfo.reduce_spider_role);
      if (index > -1) {
        sameClusterArr.splice(index, 1);
      }
    }
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const infos = await Promise.all<InfoItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<InfoItem>
    }) => item.getValue()));
    const params: SubmitTicket<TicketTypes, InfoItem[]> & { remark: string, details: { is_safe: boolean }} = {
      bk_biz_id: currentBizId,
      remark: '',
      ticket_type: TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES,
      details: {
        is_safe: !isIgnoreBusinessAccess.value,
        infos,
      },
    };
    InfoBox({
      title: t('确认缩容n个集群？', { n: totalNum.value }),
      width: 480,
      infoType: 'warning',
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'SpiderProxyScaleDown',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        })
          .catch((e) => {
            console.error('submit spider scale down error: ', e);
            window.changeConfirm = false;
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      } });
  };

  // 重置
  const handleReset = () => {
    tableData.value = [createRowData()];
    clusterNodeTypeMap.value = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .proxy-scale-down-page {
    padding-bottom: 20px;

    .top-opeartion {
      display: flex;
      width: 100%;
      height: 30px;
      justify-content: flex-end;
      align-items: flex-end;
    }

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
</style>
