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
        :title="$t('Slave提升成主库_断开同步_切换后集成成单点状态_一般用于紧急切换')" />
      <div class="page-action-box">
        <BkButton
          @click="handleShowBatchEntry">
          <DbIcon type="add" />
          {{ $t('批量录入') }}
        </BkButton>
        <div
          v-bk-tooltips="$t('安全模式下_存在业务连接时需要人工确认')"
          class="safe-action">
          <BkCheckbox
            v-model="isSafe"
            :false-label="false"
            true-label>
            <span class="safe-action-text">{{ $t('安全模式') }}</span>
          </BkCheckbox>
        </div>
      </div>
      <RenderData
        class="mt16"
        @show-master-batch-selector="handleShowMasterBatchSelector">
        <RenderDataRow
          v-for="(item, index) in tableData"
          :key="item.rowKey"
          ref="rowRefs"
          :data="item"
          :removeable="tableData.length <2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @remove="handleRemove(index)" />
      </RenderData>
      <InstanceSelector
        v-model:is-show="isShowMasterInstanceSelector"
        :panel-list="['tendbha', 'manualInput']"
        role="master"
        @change="handelMasterProxyChange" />
      <BatchEntry
        v-model:is-show="isShowBatchEntry"
        @change="handleBatchEntry" />
    </div>
    <template #action>
      <BkButton
        class="w88"
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
          class="ml8 w88"
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

  import InstanceSelector, {
    type InstanceSelectorValues,
  } from '@components/instance-selector/Index.vue';

  import BatchEntry, {
    type IValue as IBatchEntryValue,
  } from './components/BatchEntry.vue';
  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, {
    createRowData,
    type IDataRow,
  } from './components/RenderData/Row.vue';

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.masterData
      && !firstRow.slaveData
      && !firstRow.clusterData;
  };

  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isShowBatchEntry = ref(false);
  const isSubmitting  = ref(false);
  const isSafe = ref(false);

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

  // Master 批量选择
  const handleShowMasterBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };
  // Master 批量选择
  const handelMasterProxyChange = (data: InstanceSelectorValues) => {
    const ipMemo = {} as Record<string, boolean>;
    const newList = [] as IDataRow [];
    data.tendbha.forEach((proxyData) => {
      const {
        bk_host_id,
        bk_cloud_id,
        instance_address: instanceAddress,
      } = proxyData;
      const [ip] = instanceAddress.split(':');
      if (!ipMemo[ip]) {
        newList.push(createRowData({
          masterData: {
            bk_host_id,
            bk_cloud_id,
            ip,
          },
        }));
        ipMemo[ip] = true;
      }
    });
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
        ticket_type: 'MYSQL_MASTER_FAIL_OVER',
        remark: '',
        details: {
          infos: data,
          is_safe: isSafe.value,
        },
        bk_biz_id: currentBizId,
      }).then((data) => {
        window.changeConfirm = false;

        router.push({
          name: 'MySQLMasterFailover',
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
  .master-failover-page {
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
  }
</style>
