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
    <div class="mysql-proxy-add-page">
      <BkAlert
        closable
        theme="info"
        :title="$t('给集群添加Proxy实例')" />
      <div class="mt16">
        <BkButton
          @click="handleShowBatchEntry">
          <DbIcon type="add" />
          {{ $t('批量录入') }}
        </BkButton>
      </div>
      <RenderData
        class="mt16"
        @batch-select-cluster="handleShowBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length <2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @remove="handleRemove(index)" />
      </RenderData>
      <ClusterSelector
        v-model:is-show="isShowBatchSelector"
        :tab-list="clusterSelectorTabList"
        @change="handelClusterChange" />
      <BatchEntry
        v-model:is-show="isShowBatchEntry"
        @change="handleBatchEntry" />
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
          class="ml8 w-88"
          :disabled="isSubmitting">
          {{ $t('重置') }}
        </BkButton>
      </DbPopconfirm>
    </template>
  </SmartAction>
</template>

<script setup lang="tsx">
  import {
    ref,
    shallowRef,
  } from 'vue';
  import { useRouter } from 'vue-router';

  import { createTicket } from '@services/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import ClusterSelector from '@components/cluster-selector/ClusterSelector.vue';

  import BatchEntry, {
    type IValue as IBatchEntryValue,
  } from './components/BatchEntry.vue';
  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/RenderData/Row.vue';

  interface IClusterData {
    id: number,
    master_domain: string,
    bk_cloud_id: number,
  }

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.clusterData && !firstRow.proxyIp;
  };

  const clusterSelectorTabList = [ClusterTypes.TENDBHA];

  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const rowRefs = ref();
  const isShowBatchSelector = ref(false);
  const isShowBatchEntry = ref(false);
  const isSubmitting  = ref(false);

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);

  // 批量录入
  const handleShowBatchEntry = () => {
    isShowBatchEntry.value = true;
  };
  // 批量录入
  const handleBatchEntry = (list: Array<IBatchEntryValue>) => {
    const newList = list.map(item => createRowData(item));
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
    window.changeConfirm = true;
  };
  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchSelector.value = true;
  };
  // 批量选择
  const handelClusterChange = (selected: {[key: string]: Array<IClusterData>}) => {
    const newList = selected[ClusterTypes.TENDBHA].map(clusterData => createRowData({
      clusterData: {
        id: clusterData.id,
        domain: clusterData.master_domain,
        cloudId: clusterData.bk_cloud_id,
      },
    }));
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
      .then(data => createTicket({
        ticket_type: 'MYSQL_PROXY_ADD',
        remark: '',
        details: {
          infos: data,
        },
        bk_biz_id: currentBizId,
      }).then((data) => {
        window.changeConfirm = false;

        router.push({
          name: 'MySQLProxyAdd',
          params: {
            page: 'success',
          },
          query: {
            ticketId: data.id,
          },
        });
      }))
      .finally(() => {
        isSubmitting.value = false;
      });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
  };
</script>

<style lang="less">
  .mysql-proxy-add-page {
    padding-bottom: 20px;
  }
</style>
