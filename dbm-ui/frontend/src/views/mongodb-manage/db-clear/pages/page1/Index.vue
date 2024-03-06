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
    <div class="mongo-db-clear-page">
      <BkAlert
        closable
        theme="info"
        :title="t('清档：删除目标数据库数据, 数据会暂存在不可见的备份库中，只有在执行删除备份库后, 才会真正的删除数据。')" />
      <div class="title-spot mt-12 mb-10">
        {{ t('集群类型') }}<span class="required" />
      </div>
      <BkRadioGroup
        v-model="clusterType"
        style="width: 400px;"
        type="card"
        @change="handleClusterTypeChange">
        <BkRadioButton :label="ClusterTypes.MONGO_REPLICA_SET">
          {{ t('副本集集群') }}
        </BkRadioButton>
        <BkRadioButton :label="ClusterTypes.MONGO_SHARED_CLUSTER">
          {{ t('分片集群') }}
        </BkRadioButton>
      </BkRadioGroup>
      <RenderData
        class="mt16"
        :is-shard-cluster="isShardCluster"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :cluster-type="clusterType"
          :data="item"
          :is-shard-cluster="isShardCluster"
          :removeable="tableData.length < 2"
          @add="() => handleAppend(index)"
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
    <ClusterSelector
      v-model:is-show="isShowBatchSelector"
      :cluster-types="[clusterType]"
      :selected="selectedClusters"
      @change="handelClusterChange" />
  </SmartAction>
</template>
<script setup lang="tsx">
  import { InfoBox } from 'bkui-vue';
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import MongodbModel from '@services/model/mongodb/mongodb';
  import { getMongoList } from '@services/source/mongodb';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import {
    ClusterTypes,
    TicketTypes,
  } from '@common/const';

  import ClusterSelector from '@components/cluster-selector-new/Index.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/RenderData/Row.vue';

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const rowRefs = ref();
  const isShowBatchSelector = ref(false);
  const isSubmitting  = ref(false);
  const isIgnoreBusinessAccess = ref(false);
  const clusterType = ref(ClusterTypes.MONGO_REPLICA_SET);

  const tableData = shallowRef<Array<IDataRow>>([createRowData()]);
  const selectedClusters = shallowRef<{[key: string]: Array<MongodbModel>}>({
    [ClusterTypes.MONGO_SHARED_CLUSTER]: [],
  });

  const isShardCluster = computed(() => clusterType.value === ClusterTypes.MONGO_SHARED_CLUSTER);

  const totalNum = computed(() => tableData.value.filter(item => Boolean(item.clusterName)).length);

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterName
      && !firstRow.dbPatterns
      && !firstRow.ignoreDbs
      && !firstRow.tablePatterns
      && !firstRow.ignoreTables;
  };

  const handleClusterTypeChange = () => {
    tableData.value = [createRowData()];
  };

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  const generateRowDateFromRequest = (item: MongodbModel) => ({
    rowKey: item.master_domain,
    isLoading: false,
    clusterName: item.master_domain,
    clusterId: item.id,
    clusterType: item.cluster_type,
  });

  // 批量选择
  const handelClusterChange = (selected: {[key: string]: Array<MongodbModel>}) => {
    selectedClusters.value = selected;
    const list = selected[clusterType.value];
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
    const result = await getMongoList({ exact_domain: domain })
    if (result.results.length < 1) {
      return;
    }
    const item = result.results[0];
    const row = generateRowDateFromRequest(item);
    tableData.value[index] = row;
    domainMemo[domain] = true;
    selectedClusters.value[ClusterTypes.MONGO_SHARED_CLUSTER].push(item);
  };

  // 追加一个集群
  const handleAppend = (index: number) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, createRowData());
    tableData.value = dataList;
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    const domain = dataList[index].clusterName;
    dataList.splice(index, 1);
    tableData.value = dataList;
    if (domain) {
      delete domainMemo[domain];
      const clustersArr = selectedClusters.value[clusterType.value];
      selectedClusters.value[clusterType.value] = clustersArr.filter(item => item.master_domain !== domain);
    }
  };

  const handleSubmit = async () => {
    const infos = await Promise.all<any>(rowRefs.value.map((item: {
      getValue: () => Promise<any>
    }) => item.getValue()));
    const replicaSetCounts = _.flatMap(infos.map(item => item.cluster_ids)).length;
    const params = {
      bk_biz_id: currentBizId,
      ticket_type: TicketTypes.MONGODB_REMOVE_NS,
      remark: '',
      details: {
        is_safe: !isIgnoreBusinessAccess.value,
        infos,
      },
    };
    
    const title = isShardCluster.value ? t('确认清档n个分片式集群', { n: totalNum.value }) : t('确认清档n个副本集集群', { n: replicaSetCounts });
    InfoBox({
      title,
      subTitle: t('集群上的数据将会被清除掉'),
      width: 480,
      onConfirm: () => {
        isSubmitting.value = true;
        createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MongoDbClear',
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

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[clusterType.value] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .mongo-db-clear-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 20px;

      .safe-action-text {
        padding-bottom: 2px;
        border-bottom: 1px dashed #979ba5;
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
