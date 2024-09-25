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
    <div class="sqlserver-manage-db-clear-page">
      <BkAlert
        closable
        theme="info"
        :title="
          t('清档：删除目标数据库数据, 数据会暂存在不可见的备份库中，只有在执行删除备份库后, 才会真正的删除数据。')
        " />
      <RenderData
        class="mt16"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @remove="handleRemove(index)" />
      </RenderData>
      <ClusterSelector
        v-model:is-show="isShowBatchSelector"
        :cluster-types="[ClusterTypes.SQLSERVER_HA, ClusterTypes.SQLSERVER_SINGLE]"
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
        :content="t('重置将会情况当前填写的所有内容_请谨慎操作')"
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
  import { ref, shallowRef, type UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import SqlServerHaModel from '@services/model/sqlserver/sqlserver-ha';
  import SqlServerSingleModel from '@services/model/sqlserver/sqlserver-single';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/Index.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

  const { t } = useI18n();
  const router = useRouter();

  const rowRefs = ref();
  const isShowBatchSelector = ref(false);
  const isSubmitting = ref(false);

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);

  const selectedClusters = shallowRef<{ [key: string]: (SqlServerSingleModel | SqlServerHaModel)[] }>({
    [ClusterTypes.SQLSERVER_HA]: [],
    [ClusterTypes.SQLSERVER_SINGLE]: [],
  });

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return (
      !firstRow.clusterData &&
      !firstRow.cleanMode &&
      firstRow.cleanDbsPatterns.length < 1 &&
      firstRow.cleanIgnoreDbsPatterns.length < 1 &&
      firstRow.ignoreCleanTables.length < 1
    );
  };

  useTicketCloneInfo({
    type: TicketTypes.SQLSERVER_CLEAR_DBS,
    onSuccess(cloneData) {
      tableData.value = cloneData.map((item) =>
        createRowData({
          clusterData: {
            id: item.cluster.id,
            domain: item.cluster.immute_domain,
            cloudId: item.cluster.bk_cloud_id,
          },
          cleanMode: item.clean_mode,
          cleanDbsPatterns: item.clean_dbs_patterns,
          cleanIgnoreDbsPatterns: item.clean_ignore_dbs_patterns,
          cleanTables: item.clean_tables,
          ignoreCleanTables: item.ignore_clean_tables,
          cleanDbs: item.clean_dbs,
        }),
      );
    },
  });

  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };

  // 批量选择
  const handelClusterChange = (selected: UnwrapRef<typeof selectedClusters>) => {
    selectedClusters.value = selected;
    const list = _.flatten(Object.values(selected));
    const newList = list.reduce((result, item) => {
      const row = createRowData({
        clusterData: {
          id: item.id,
          domain: item.master_domain,
          cloudId: item.bk_cloud_id,
        },
      });
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

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()))
      .then((data) =>
        createTicket({
          ticket_type: TicketTypes.SQLSERVER_CLEAR_DBS,
          remark: '',
          details: {
            infos: data,
          },
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        }),
      )
      .then((data) => {
        window.changeConfirm = false;
        router.push({
          name: 'sqlServerDBClear',
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
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedClusters.value = {
      [ClusterTypes.SQLSERVER_HA]: [],
      [ClusterTypes.SQLSERVER_SINGLE]: [],
    };
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .sqlserver-manage-db-clear-page {
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
