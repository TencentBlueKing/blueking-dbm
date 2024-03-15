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
    <div class="proxy-replace-page">
      <BkAlert
        closable
        theme="info"
        :title="t('对集群的Proxy实例进行替换')" />
      <div class="page-action-box mt16">
        <BkButton @click="handleShowBatchEntry">
          <DbIcon type="add" />
          {{ t('批量录入') }}
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
          :removeable="tableData.length < 2"
          @add="(payload: Array<IDataRow>) => handleAppend(index, payload)"
          @remove="handleRemove(index)" />
      </RenderData>
      <div class="safe-action">
        <BkCheckbox
          v-model="isSafe"
          v-bk-tooltips="t('如忽略_在有连接的情况下Proxy也会执行替换')"
          :false-label="false"
          true-label>
          <span class="safe-action-text">{{ t('忽略业务连接') }}</span>
        </BkCheckbox>
      </div>
      <InstanceSelector
        v-model:is-show="isShowBatchProxySelector"
        :cluster-types="[ClusterTypes.TENDBHA]"
        :selected="selectedIntances"
        :tab-list-config="tabListConfig"
        @change="handelProxySelectorChange" />
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
  import { ref, shallowRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TendbhaInstanceModel from '@services/model/mysql/tendbha-instance';
  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import InstanceSelector, {
    type InstanceSelectorValues,
    type PanelListType,
  } from '@components/instance-selector/Index.vue';

  import BatchEntry, { type IValue as IBatchEntryValue } from './components/BatchEntry.vue';
  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.originProxyIp && !firstRow.targetProxyIp;
  };

  const router = useRouter();
  const { currentBizId } = useGlobalBizs();
  const { t } = useI18n();

  const rowRefs = ref();
  const isShowBatchProxySelector = ref(false);
  const isShowBatchEntry = ref(false);
  const isSubmitting = ref(false);
  const isSafe = ref(false);

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);
  const selectedIntances = shallowRef<InstanceSelectorValues<TendbhaInstanceModel>>({ [ClusterTypes.TENDBHA]: [] });

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: [
      {
        name: t('目标Proxy'),
        tableConfig: {
          firsrColumn: {
            label: 'proxy',
            field: 'instance_address',
            role: 'proxy',
          },
        },
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  // 批量录入
  const handleShowBatchEntry = () => {
    isShowBatchEntry.value = true;
  };
  // 批量录入
  const handleBatchEntry = (list: Array<IBatchEntryValue>) => {
    if (list.length === 0) {
      return;
    }

    const newList = list.map((item) => createRowData(item));
    if (checkListEmpty(tableData.value)) {
      tableData.value = newList;
    } else {
      tableData.value = [...tableData.value, ...newList];
    }
  };
  // 批量选择
  const handleShowBatchSelector = () => {
    isShowBatchProxySelector.value = true;
  };
  // 批量选择
  const handelProxySelectorChange = (data: InstanceSelectorValues<TendbhaInstanceModel>) => {
    selectedIntances.value = data;
    const newList = data.tendbha.map(item => createRowData({
      originProxyIp: item,
    }));
    tableData.value = newList;
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
    const instanceAddress = tableData.value[index].originProxyIp?.instance_address;
    if (instanceAddress) {
      const clustersArr = selectedIntances.value[ClusterTypes.TENDBHA];
      // eslint-disable-next-line max-len
      selectedIntances.value[ClusterTypes.TENDBHA] = clustersArr.filter(item => item.instance_address !== instanceAddress);
    }
    const dataList = [...tableData.value];
    dataList.splice(index, 1);
    tableData.value = dataList;
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()))
      .then((data) =>
        createTicket({
          ticket_type: 'MYSQL_PROXY_SWITCH',
          remark: '',
          details: {
            infos: data,
            is_safe: isSafe.value,
          },
          bk_biz_id: currentBizId,
        }).then((data) => {
          window.changeConfirm = false;

          router.push({
            name: 'MySQLProxyReplace',
            params: {
              page: 'success',
            },
            query: {
              ticketId: data.id,
            },
          });
        }),
      )
      .finally(() => {
        isSubmitting.value = false;
      });
  };

  const handleReset = () => {
    tableData.value = [createRowData()];
    selectedIntances.value[ClusterTypes.TENDBHA] = [];
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .proxy-replace-page {
    padding-bottom: 20px;

    .page-action-box {
      display: flex;
      align-items: center;
    }

    .safe-action {
      margin-top: 20px;

      .safe-action-text {
        padding-bottom: 2px;
        border-bottom: 1px dashed #979ba5;
      }
    }
  }
</style>
