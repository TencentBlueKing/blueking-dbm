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
          :inputed-clusters="inputedClusters"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @cluster-input-finish="(domainObj: RedisModel) => handleChangeCluster(index, domainObj)"
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
        :content="t('重置将会清空当前填写的所有内容_请谨慎操作')"
        :title="t('确认重置页面')">
        <BkButton
          class="ml-8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
    <ClusterSelector
      v-model:is-show="isShowMasterInstanceSelector"
      :cluster-types="[ClusterTypes.REDIS]"
      :selected="selectedClusters"
      :tab-list-config="tabListConfig"
      @change="handelClusterChange" />
  </SmartAction>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import RedisModel from '@services/model/redis/redis';
  import { getRedisList } from '@services/source/redis';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector, { type TabItem } from '@components/cluster-selector/Index.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow, type InfoItem } from './components/Row.vue';

  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.REDIS_SCALE_UPDOWN,
    onSuccess(cloneData) {
      tableData.value = cloneData;
      window.changeConfirm = true;
    },
  });

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting = ref(false);
  const tableData = ref([createRowData()]);
  const selectedClusters = shallowRef<{ [key: string]: Array<RedisModel> }>({ [ClusterTypes.REDIS]: [] });

  const inputedClusters = computed(() => tableData.value.map((item) => item.targetCluster));
  const totalNum = computed(() => tableData.value.filter((item) => Boolean(item.targetCluster)).length);

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  const tabListConfig = {
    [ClusterTypes.REDIS]: {
      getResourceList: (params: ServiceParameters<typeof getRedisList>) =>
        getRedisList({
          cluster_type: [
            ClusterTypes.TWEMPROXY_REDIS_INSTANCE,
            ClusterTypes.PREDIXY_REDIS_CLUSTER,
            ClusterTypes.PREDIXY_TENDISPLUS_CLUSTER,
            ClusterTypes.TWEMPROXY_TENDIS_SSD_INSTANCE,
          ].join(','),
          ...params,
        }),
    },
  } as unknown as Record<ClusterTypes, TabItem>;

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.targetCluster;
  };

  // 根据集群选择返回的数据加工成table所需的数据
  const generateRowDateFromRequest = (data: RedisModel) => ({
    rowKey: data.master_domain,
    isLoading: false,
    targetCluster: data.master_domain,
    currentSepc: data.cluster_spec.spec_name,
    clusterId: data.id,
    bkCloudId: data.bk_cloud_id,
    clusterTypeName: data.cluster_type_name,
    clusterStats: data.cluster_stats,
    shardNum: data.cluster_shard_num,
    groupNum: data.machine_pair_cnt,
    machineCount: data.redis_master.length,
    version: data.major_version,
    clusterType: data.cluster_spec.spec_cluster_type,
    currentCapacity: {
      used: 1,
      total: data.cluster_capacity,
    },
    spec: data.cluster_spec,
    targetShardNum: 0,
    targetGroupNum: 0,
  });

  // 批量选择
  const handelClusterChange = (selected: Record<string, RedisModel[]>) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.REDIS];
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
    isShowMasterInstanceSelector.value = true;
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, domainObj: RedisModel) => {
    const row = generateRowDateFromRequest(domainObj);
    tableData.value[index] = row;
    domainMemo[domainObj.master_domain] = true;
    selectedClusters.value[ClusterTypes.REDIS].push(domainObj);
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };
  // 删除一个集群
  const handleRemove = (index: number) => {
    const { targetCluster } = tableData.value[index];
    tableData.value.splice(index, 1);
    delete domainMemo[targetCluster];
    const clustersArr = selectedClusters.value[ClusterTypes.REDIS];
    // eslint-disable-next-line max-len
    selectedClusters.value[ClusterTypes.REDIS] = clustersArr.filter((item) => item.master_domain !== targetCluster);
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    try {
      isSubmitting.value = true;
      const infos = await Promise.all<InfoItem[]>(
        rowRefs.value.map((item: { getValue: () => Promise<InfoItem> }) => item.getValue()),
      );
      const params = {
        bk_biz_id: currentBizId,
        ticket_type: TicketTypes.REDIS_SCALE_UPDOWN,
        details: {
          ip_source: 'resource_pool',
          infos,
        },
      };

      await createTicket(params).then((data) => {
        window.changeConfirm = false;
        router.push({
          name: 'RedisCapacityChange',
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
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.REDIS] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .master-failover-page {
    padding-bottom: 20px;
  }
</style>
