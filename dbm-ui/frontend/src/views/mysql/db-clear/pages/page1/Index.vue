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
    <div class="sipder-manage-db-clear-page">
      <BkAlert
        closable
        theme="info"
        :title="t('清档_删除目标数据库数据_数据会暂存在不可见的备份库中_只有在执行删除备份库后_才会真正的删除数据')" />
      <div class="db-clear-operations mt16">
        <BkButton
          class="db-clear-batch"
          @click="() => (isShowBatchInput = true)">
          <i class="db-icon-add" />
          {{ t('批量录入') }}
        </BkButton>
      </div>
      <RenderData
        class="mt16"
        @batch-edit="handleBatchEditColumn"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :cluster-types="clusterTypes"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @clone="(payload: IDataRow) => handleClone(index, payload)"
          @cluster-input-finish="(clusterId: number) => handleChangeCluster(index, clusterId)"
          @remove="handleRemove(index)" />
      </RenderData>
      <div class="page-action-box">
        <div v-bk-tooltips="t('安全模式下_存在业务连接时需要人工确认')">
          <BkCheckbox
            v-model="isSafe"
            :false-label="false"
            true-label>
            <span class="safe-action-text">{{ t('安全模式') }}</span>
          </BkCheckbox>
        </div>
      </div>
      <TicketRemark v-model="remark" />
      <BatchInput
        v-model:is-show="isShowBatchInput"
        @change="handleBatchInput" />
      <ClusterSelector
        v-model:is-show="isShowBatchSelector"
        :cluster-types="[ClusterTypes.TENDBHA, ClusterTypes.TENDBSINGLE]"
        only-one-type
        :selected="selectedClusters"
        @change="handelClusterChange" />
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
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TendbhaModel from '@services/model/mysql/tendbha';
  import { queryClusters } from '@services/source/mysqlCluster';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';
  import TicketRemark from '@components/ticket-remark/Index.vue';

  import BatchInput, { type InputItem } from './components/BatchInput.vue';
  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow, type IDataRowBatchKey } from './components/RenderData/Row.vue';

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_HA_TRUNCATE_DATA,
    onSuccess(cloneData) {
      const { isSafeStatus, tableDataList } = cloneData;
      tableData.value = tableDataList;
      isSafe.value = isSafeStatus;
      remark.value = cloneData.remark;
      window.changeConfirm = true;
    },
  });

  // 单据克隆
  useTicketCloneInfo({
    type: TicketTypes.MYSQL_SINGLE_TRUNCATE_DATA,
    onSuccess(cloneData) {
      const { isSafeStatus, tableDataList } = cloneData;
      tableData.value = tableDataList;
      isSafe.value = isSafeStatus;
      window.changeConfirm = true;
    },
  });

  const rowRefs = ref();
  const isShowBatchSelector = ref(false);
  const isSafe = ref(false);
  const isSubmitting = ref(false);
  const isShowBatchInput = ref(false);
  const tableData = ref<Array<IDataRow>>([createRowData({})]);
  const remark = ref('');

  const selectedClusters = shallowRef<{ [key: string]: Array<TendbhaModel> }>({
    [ClusterTypes.TENDBHA]: [],
    [ClusterTypes.TENDBSINGLE]: [],
  });

  const clusterTypes = computed(() => tableData.value.map((item) => item.clusterData?.type as string));

  // 集群域名是否已存在表格的映射表
  let domainMemo: Record<string, boolean> = {};

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return (
      !firstRow.clusterData &&
      !firstRow.dbPatterns &&
      !firstRow.ignoreDbs &&
      !firstRow.tablePatterns &&
      !firstRow.ignoreTables
    );
  };

  /**
   * 批量录入
   */
  async function handleBatchInput(list: Array<InputItem>) {
    const domains = list.map((item) => item.cluster);
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
      const { cluster } = item;
      const currentCluster = clusterInfoMap[cluster];
      return {
        ...createRowData(),
        clusterData: {
          id: currentCluster.id,
          domain: cluster,
          type: currentCluster.cluster_type,
        },
        dbPatterns: item.dbs,
        tablePatterns: item.tables,
        ignoreDbs: item.ignoreDbs,
        ignoreTables: item.ignoreTables,
      };
    });
    if (checkListEmpty(tableData.value)) {
      tableData.value = formatList;
    } else {
      tableData.value = [...tableData.value, ...formatList];
    }
    window.changeConfirm = true;
  }

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  // 输入集群后查询集群信息并填充到table
  const handleChangeCluster = async (index: number, clusterId: number) => {
    if (tableData.value[index].clusterData?.id === clusterId) {
      return;
    }

    const resultList = await queryClusters({
      cluster_filters: [
        {
          id: clusterId,
        },
      ],
      bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
    });
    if (resultList.length < 1) {
      return;
    }
    const item = resultList[0];
    const domain = item.master_domain;
    const row = createRowData({
      clusterData: {
        id: item.id,
        domain,
        type: item.cluster_type,
      },
    });
    tableData.value[index] = row;
    domainMemo[domain] = true;
    selectedClusters.value[item.cluster_type].push(item);
  };

  // 批量选择
  const handelClusterChange = (selected: { [key: string]: Array<TendbhaModel> }) => {
    selectedClusters.value = selected;
    const selectedList = Object.keys(selected).reduce((list: TendbhaModel[], key) => list.concat(...selected[key]), []);
    const newList = selectedList.reduce<IDataRow[]>((result, item) => {
      const domain = item.master_domain;
      if (!domainMemo[domain]) {
        const row = createRowData({
          clusterData: {
            id: item.id,
            domain: item.master_domain,
            type: item.cluster_type,
          },
        });
        result.push(row);
        domainMemo[domain] = true;
      }
      return result;
    }, []);
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };

  const handleBatchEditColumn = (value: string | string[], filed: IDataRowBatchKey) => {
    if (!value || checkListEmpty(tableData.value)) {
      return;
    }
    tableData.value.forEach((row) => {
      Object.assign(row, {
        [filed]: value,
      });
    });
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

  // 复制行数据
  const handleClone = (index: number, sourceData: IDataRow) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, sourceData);
    tableData.value = dataList;
    setTimeout(() => {
      rowRefs.value[rowRefs.value.length - 1].getValue();
    });
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()))
      .then((data) => {
        const clusterTypes = _.uniq(tableData.value.map((item) => item.clusterData?.type));
        return createTicket({
          ticket_type:
            clusterTypes[0] === ClusterTypes.TENDBHA
              ? TicketTypes.MYSQL_HA_TRUNCATE_DATA
              : TicketTypes.MYSQL_SINGLE_TRUNCATE_DATA,
          remark: remark.value,
          details: {
            infos: data.map((item) =>
              Object.assign(item, {
                force: !isSafe.value,
              }),
            ),
          },
          bk_biz_id: currentBizId,
        }).then((data) => {
          window.changeConfirm = false;
          router.push({
            name: 'MySQLDBClear',
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
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    remark.value = '';
    selectedClusters.value[ClusterTypes.TENDBHA] = [];
    selectedClusters.value[ClusterTypes.TENDBSINGLE] = [];
    domainMemo = {};
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .sipder-manage-db-clear-page {
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
  }
</style>
