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
        :title="t('缩容Shard节点数：xxx')" />
      <RenderData
        class="mt16"
        @show-master-batch-selector="handleShowMasterBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :inputed-clusters="inputedClusters"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @cluster-input-finish="(domain: string) => handleChangeCluster(index, domain)"
          @remove="handleRemove(index)" />
      </RenderData>
      <div class="bottom-opeartion">
        <BkCheckbox
          v-model="isIgnoreBusinessAccess"
          style="padding-top: 6px;" />
        <span
          v-bk-tooltips="{
            content: t('如忽略_有连接的情况下也会执行'),
            theme: 'dark',
          }"
          class="ml-6 force-switch">{{ t('忽略业务连接') }}</span>
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
      :cluster-types="[ClusterTypes.MONGO_SHARED_CLUSTER, ClusterTypes.MONGO_REPLICA_SET]"
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

  import ClusterSelector, {
    type TabItem,
  } from '@components/cluster-selector-new/Index.vue';

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

  const selectedClusters = shallowRef<{[key: string]: Array<MongoDBModel>}>({
    [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
    [ClusterTypes.MONGO_REPLICA_SET]: [],
  });

  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.clusterName)).length);
  const inputedClusters = computed(() => tableData.value.map(item => item.clusterName));

  const tabListConfig = {
    [ClusterTypes.MONGO_REPLICA_SET]: {
      name: t('副本集集群'),
      showPreviewResultTitle: true,
    },
    [ClusterTypes.MONGO_SHARED_CLUSTER]: {
      name: t('分片集群'),
      showPreviewResultTitle: true,
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
    clusterType: item.cluster_type,
    clusterTypeText: item.clusterTypeText,
    currentNodeNum: item.shard_node_count,
  });

  // 批量选择
  const handelClusterChange = (selected: {[key: string]: Array<MongoDBModel>}) => {
    selectedClusters.value = selected;
    let list: MongoDBModel[] = [];
    if (selected[ClusterTypes.MONGO_REPLICA_SET]) {
      list = selected[ClusterTypes.MONGO_REPLICA_SET];
    }
    if (selected[ClusterTypes.MONGO_SHARED_CLUSTER]) {
      list = [...list, ...selected[ClusterTypes.MONGO_SHARED_CLUSTER]];
    }
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
    const list = result.results.filter(item => item.master_domain === domain);
    if (list.length === 0) {
      return;
    }
    const item = list[0];
    const row = generateRowDateFromRequest(item);
    tableData.value[index] = row;
    domainMemo[domain] = true;
    selectedClusters.value[row.clusterType].push(item);
  };

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    tableData.value.splice(index + 1, 0, ...appendList);
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const {
      clusterName,
      clusterType,
    } = tableData.value[index];
    tableData.value.splice(index, 1);
    delete domainMemo[clusterName];
    const clustersArr = selectedClusters.value[clusterType];
    selectedClusters.value[clusterType] = clustersArr.filter(item => item.master_domain !== clusterName);
  };

  // 点击提交按钮
  const handleSubmit = async () => {
    const infos = await Promise.all<InfoItem[]>(rowRefs.value.map((item: {
      getValue: () => Promise<InfoItem>
    }) => item.getValue()));
    const params = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.MONGODB_REDUCE_SHARD_NODES,
      details: {
        is_safe: !isIgnoreBusinessAccess.value,
        infos,
      },
    };
    
    InfoBox({
      title: t('确认缩容n个集群的Shard节点数', { n: totalNum.value }),
      width: 400,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MongoShardScaleDown',
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
      } });
  };

  // 重置
  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER] = [];
    selectedClusters.value[ClusterTypes.MONGO_REPLICA_SET] = [];
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
        border-bottom: 1px dashed #63656E;
      }
    }
  }
</style>
