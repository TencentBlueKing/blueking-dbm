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
    <div class="mysql-db-rename-page">
      <BkAlert
        closable
        :title="t('DB重命名_database重命名')" />
      <div class="db-rename-operations">
        <BkButton
          class="db-rename-batch"
          @click="() => (isShowBatchInput = true)">
          <DbIcon type="add" />
          {{ t('批量录入') }}
        </BkButton>
      </div>
      <RenderData @batch-select-cluster="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload) => handleAppend(index, payload)"
          @remove="handleRemove(index)" />
      </RenderData>
      <div class="bottom-opeartion">
        <BkCheckbox
          v-model="isForce"
          style="padding-top: 6px" />
        <span
          v-bk-tooltips="{
            content: t('如忽略_有连接的情况下也会执行'),
            theme: 'dark',
          }"
          class="ml-6 force-switch">
          {{ t('忽略业务连接') }}
        </span>
      </div>
    </div>
    <template #action>
      <BkButton
        class="mr-8 w-88"
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
  <BatchInput
    v-model:is-show="isShowBatchInput"
    @change="handleBatchInput" />
  <ClusterSelector
    v-model:is-show="isShowBatchSelector"
    :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
    only-one-type
    :selected="selectedClusters"
    @change="handleBatchSelectorChange" />
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { queryClusters } from '@services/source/mysqlCluster';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  import { messageError } from '@utils';

  import BatchInput from './components/BatchInput.vue';
  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

  const { t } = useI18n();
  const globalBizsStore = useGlobalBizs();
  const router = useRouter();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_HA_RENAME_DATABASE,
    onSuccess(cloneData) {
      const { force, tableDataList } = cloneData;
      tableData.value = tableDataList;
      isForce.value = force;
      window.changeConfirm = true;
    },
  });

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_SINGLE_RENAME_DATABASE,
    onSuccess(cloneData) {
      const { force, tableDataList } = cloneData;
      tableData.value = tableDataList;
      isForce.value = force;
      window.changeConfirm = true;
    },
  });

  const rowRefs = ref();
  const isShowBatchInput = ref(false);
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);
  const clusterInfoMap: Map<string, TendbhaModel> = reactive(new Map());
  const isForce = ref(false);
  const tableData = ref<Array<IDataRow>>([createRowData({})]);

  const selectedClusters = shallowRef<{ [key: string]: Array<TendbhaModel> }>({
    [ClusterTypes.TENDBHA]: [],
    [ClusterTypes.TENDBSINGLE]: [],
  });

  let domainMemo: Record<string, boolean> = {};

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }

    const [firstRow] = list;
    return !firstRow.clusterData && !firstRow.fromDatabase && !firstRow.toDatabase;
  };

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
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
    const domain = dataList[index].clusterData?.domain;
    const clusterType = dataList[index].clusterData?.type;
    dataList.splice(index, 1);
    tableData.value = dataList;
    if (domain && clusterType) {
      delete domainMemo[domain];
      const clustersArr = selectedClusters.value[clusterType];
      selectedClusters.value[clusterType] = clustersArr.filter((item) => item.master_domain !== domain);
    }
  };

  /**
   * 批量录入
   */
  async function handleBatchInput(list: Array<{ domain: string; origin: string; rename: string }>) {
    const domains = list.map((item) => item.domain);
    const clusterInfos = await queryClusters({
      cluster_filters: domains.map((domain) => ({
        immute_domain: domain,
      })),
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });
    const clusterInfoMap = clusterInfos.reduce<Record<string, TendbhaModel>>(
      (results, item) =>
        Object.assign(results, {
          [item.master_domain]: item,
        }),
      {},
    );
    const formatList = list.map((item) => {
      const { domain } = item;
      const currentCluster = clusterInfoMap[domain];
      return {
        ...createRowData(),
        clusterData: {
          id: currentCluster.id,
          domain,
          type: currentCluster.cluster_type,
        },
        fromDatabase: item.origin,
        toDatabase: item.rename,
      };
    });
    if (checkListEmpty(tableData.value)) {
      tableData.value = formatList;
    } else {
      tableData.value = [...tableData.value, ...formatList];
    }
    window.changeConfirm = true;
  }

  /**
   * 集群选择器批量选择
   */
  function handleBatchSelectorChange(selected: Record<string, Array<TendbhaModel>>) {
    selectedClusters.value = selected;
    const selectedList = Object.keys(selected).reduce<TendbhaModel[]>((list, key) => list.concat(...selected[key]), []);
    const newList = selectedList.reduce<IDataRow[]>((results, item) => {
      const domain = item.master_domain;
      clusterInfoMap.set(domain, item);
      if (!domainMemo[domain]) {
        const row = createRowData({
          clusterData: {
            id: item.id,
            domain: item.master_domain,
            type: item.cluster_type,
          },
        });
        results.push(row);
        domainMemo[domain] = true;
      }
      return results;
    }, []);

    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  }

  function handleSubmit() {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()))
      .then((data) => {
        const clusterTypes = _.uniq(tableData.value.map((item) => item.clusterData?.type));
        // 限制只能提同一种类型的集群，否则提示
        if (clusterTypes.length > 1) {
          messageError('只允许提交一种集群类型');
          return Promise.reject();
        }

        const params = {
          ticket_type:
            clusterTypes[0] === ClusterTypes.TENDBHA
              ? TicketTypes.MYSQL_HA_RENAME_DATABASE
              : TicketTypes.MYSQL_SINGLE_RENAME_DATABASE,
          bk_biz_id: globalBizsStore.currentBizId,
          details: {
            force: isForce.value,
            infos: data,
          },
        };

        return createTicket(params).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MySQLDBRename',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        });
      })
      .finally(() => {
        isSubmitting.value = false;
      });
  }

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value[ClusterTypes.TENDBHA] = [];
    selectedClusters.value[ClusterTypes.TENDBSINGLE] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .mysql-db-rename-page {
    padding-bottom: 20px;

    .db-rename-operations {
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .db-rename-batch {
      margin: 16px 0;

      .db-icon-add {
        margin-right: 4px;
        color: @gray-color;
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
