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
    <div class="master-failover-page">
      <BkAlert
        closable
        theme="info"
        :title="t('集群容量变更：通过部署新集群来实现原集群的扩容或缩容（集群分片数不变），可以指定新的版本')" />
      <RenderData
        class="mt16"
        @show-batch-selector="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          :versions-map="versionsMap"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </RenderData>
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :disabled="totalNum === 0"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        {{ t('提交') }}
      </BkButton>
      <DbPopconfirm
        :confirm-handler="handleReset"
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
    <ClusterSelector
      v-model:is-show="isShowSelector"
      :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
      :selected="selectedClusters"
      @change="handelClusterChange" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { getMongoList } from '@services/source/mongodb';
  import { createTicket } from '@services/source/ticket';
  import { getClusterTypeToVersions } from '@services/source/version';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector-new/Index.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow, type InfoItem } from './components/Row.vue';

  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const rowRefs = ref();
  const isShowSelector = ref(false);
  const isSubmitting = ref(false);
  const tableData = ref([createRowData()]);
  const versionsMap = ref<Record<string, string[]>>({});

  const selectedClusters = shallowRef<{ [key: string]: Array<MongodbModel> }>({
    [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
  });

  const totalNum = computed(() => tableData.value.filter((item) => Boolean(item.clusterName)).length);

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  const queryDBVersions = async () => {
    const ret = await getClusterTypeToVersions();
    versionsMap.value = ret;
  };

  queryDBVersions();

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterName;
  };

  // 根据集群选择返回的数据加工成table所需的数据
  const generateRowDateFromRequest = (data: MongodbModel) => ({
    rowKey: data.master_domain,
    isLoading: false,
    clusterName: data.master_domain,
    currentSepc: data.mongodb[0].spec_config.name,
    shardSpecName: data.shard_spec,
    clusterId: data.id,
    machineType: data.machine_type,
    machinePair: data.mongodb_machine_pair,
    machineNum: data.mongodb_machine_num,
    clusterType: data.cluster_type,
    shardNum: data.shard_num,
    shardNodeCount: data.shard_node_count,
    bkCloudId: data.bk_cloud_id,
    currentCapacity: {
      used: 0,
      total: 1,
    },
    targetShardNum: 0,
    targetGroupNum: 0,
    spec: data.mongodb[0].spec_config,
  });

  // 批量选择
  const handelClusterChange = (selected: Record<string, MongodbModel[]>) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.MONGO_SHARED_CLUSTER];
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

  // Master 批量选择
  const handleShowBatchSelector = () => {
    isShowSelector.value = true;
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, domain: string) => {
    if (!domain) {
      const cluster = tableData.value[index].clusterName;
      domainMemo[cluster] = false;
      tableData.value[index].clusterName = '';
      return;
    }
    tableData.value[index].isLoading = true;
    const result = await getMongoList({ exact_domain: domain }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (result.results.length === 0) {
      return;
    }

    const data = result.results[0];
    const row = generateRowDateFromRequest(data);
    tableData.value[index] = row;
    domainMemo[domain] = true;
    selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER].push(data);
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const { clusterName } = tableData.value[index];
    tableData.value.splice(index, 1);
    delete domainMemo[clusterName];
    const clustersArr = selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER];
    selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER] = clustersArr.filter(
      (item) => item.master_domain !== clusterName,
    );
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const infos = await Promise.all<InfoItem[]>(
      rowRefs.value.map((item: { getValue: () => Promise<InfoItem> }) => item.getValue()),
    );
    const params = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.MONGODB_SCALE_UPDOWN,
      details: {
        ip_source: 'resource_pool',
        infos,
      },
    };

    InfoBox({
      title: t('确认提交n个集群容量变更任务', { n: totalNum.value }),
      width: 480,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params)
          .then((data) => {
            window.changeConfirm = false;
            router.push({
              name: 'MongoCapacityChange',
              params: {
                page: 'success',
              },
              query: {
                ticketId: data.id,
              },
            });
          })
          .finally(() => {
            isSubmitting.value = false;
          });
      },
    });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .master-failover-page {
    padding-bottom: 20px;
  }
</style>
