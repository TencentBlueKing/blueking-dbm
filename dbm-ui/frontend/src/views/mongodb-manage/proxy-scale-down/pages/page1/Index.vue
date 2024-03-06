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
        :title="t('缩容接入层：减加集群的Proxy数量，但集群Proxy数量不能少于2')" />
      <RenderData
        class="mt16"
        @show-master-batch-selector="handleShowMasterBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </RenderData>
      <div class="bottom-opeartion">
        <BkCheckbox
          v-model="isIgnoreBusinessAccess"
          style="padding-top: 6px" />
        <span
          v-bk-tooltips="{
            content: t('如忽略_有连接的情况下也会执行'),
            theme: 'dark',
          }"
          class="ml-6 force-switch" >{{ t('忽略业务连接') }}</span>
      </div>
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
      v-model:is-show="isShowClusterSelector"
      :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER]"
      :selected="selectedClusters"
      :tab-list-config="tabListConfig"
      @change="handelClusterChange" />
  </SmartAction>
</template>

<script setup lang="ts">
  import { InfoBox } from 'bkui-vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import MongoDBModel from '@services/model/mongodb/mongodb';
  import { getMongoList } from '@services/source/mongodb';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector, { type TabItem }  from '@components/cluster-selector-new/Index.vue';

  import RenderData from './components/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/Row.vue';

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterName;
  };

  const router = useRouter();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const isIgnoreBusinessAccess = ref(false);
  const rowRefs = ref();
  const isShowClusterSelector = ref(false);
  const isSubmitting  = ref(false);
  const tableData = ref([createRowData()]);
  const bkCloudId = ref<number>();

  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.clusterName)).length);
  const selectedClusters = shallowRef<{[key: string]: Array<MongoDBModel>}>({
    [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
  });

  const tabListConfig = {
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      disabledRowConfig: {
        handler: (data: MongoDBModel) => data.mongos.length < 3,
        tip: t('Proxy数量不足，至少 3 台'),
      },
    },
  } as unknown as Record<ClusterTypes, TabItem>;
  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  // Master 批量选择
  const handleShowMasterBatchSelector = () => {
    isShowClusterSelector.value = true;
  };

  // 根据集群选择返回的数据加工成table所需的数据
  const generateRowDateFromRequest = (item: MongoDBModel) => ({
    rowKey: item.master_domain,
    isLoading: false,
    clusterName: item.master_domain,
    clusterId: item.id,
    shardNum: item.shard_num,
    affinity: item.disaster_tolerance_level,
    machineNum: item.replicaset_machine_num,
    currentSpec: {
      ...item.mongos[0].spec_config,
      count: item.shard_node_count,
    },
    reduceIpList: item.mongos.map(item => ({
      label: item.ip,
      value: item.ip,
      disabled: false,
      ...item,
    })),
  });

  // 批量选择
  const handelClusterChange = (selected: {[key: string]: Array<MongoDBModel>}) => {
    selectedClusters.value = selected;
    const list = selected[ClusterTypes.MONGO_SHARED_CLUSTER];
    const newList: IDataRow[] = [];
    if (bkCloudId.value === undefined) {
      bkCloudId.value = list[0].bk_cloud_id;
    }
    for (const item of list) {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = generateRowDateFromRequest(item);
        newList.push(row);
        domainMemo[domain] = true;
      }
    }
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
      const { clusterName } = tableData.value[index];
      domainMemo[clusterName] = false;
      tableData.value[index].clusterName = '';
      return;
    }
    tableData.value[index].isLoading = true;
    const result = await getMongoList({ exact_domain: domain }).finally(() => {
      tableData.value[index].isLoading = false;
    });
    if (result.results.length < 1) {
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
    selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER] = clustersArr.filter(item => item.master_domain !== clusterName);
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const infos = await Promise.all(rowRefs.value.map((item: {
      getValue: () => Promise<any>
    }) => item.getValue()));
    const params = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.MONGODB_REDUCE_MONGOS,
      details: {
        is_safe: !isIgnoreBusinessAccess.value,
        infos,
      },
    };

    InfoBox({
      title: t('确认缩容n个集群', { n: totalNum.value }),
      width: 400,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MongoProxyScaleDown',
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
      }
    });
  };

  // 重置
  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less" scoped>
  .proxy-scale-down-page {
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

    .bottom-opeartion {
      display: flex;
      width: 100%;
      height: 30px;
      align-items: flex-end;

      .force-switch {
        font-size: 12px;
        border-bottom: 1px dashed #63656e;
      }
    }
  }
</style>
