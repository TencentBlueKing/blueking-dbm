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
    <div class="mysql-master-slave-swap-page">
      <BkAlert
        closable
        theme="info"
        :title="t('同机器所有集群都完成主从关系互切')" />
      <div class="page-action-box">
        <BkButton @click="handleShowBatchEntry">
          <DbIcon type="add" />
          {{ t('批量录入') }}
        </BkButton>
      </div>
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
          @remove="handleRemove(index)" />
      </RenderData>
      <div class="item-block">
        <BkCheckbox v-model="formData.is_check_process">
          {{ t('检查业务来源的连接') }}
        </BkCheckbox>
      </div>
      <div class="item-block">
        <BkCheckbox v-model="formData.is_check_delay">
          {{ t('检查主从同步延迟') }}
        </BkCheckbox>
      </div>
      <div class="item-block">
        <BkCheckbox v-model="formData.is_verify_checksum">
          {{ t('检查主从数据校验结果') }}
        </BkCheckbox>
      </div>
      <InstanceSelector
        v-model:is-show="isShowMasterInstanceSelector"
        :cluster-types="[ClusterTypes.TENDBHA]"
        :selected="selectedIps"
        :tab-list-config="tabListConfig"
        @change="handelMasterProxyChange" />
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
    return !firstRow.masterData && !firstRow.slaveData && !firstRow.clusterData;
  };

  const router = useRouter();
  const { t } = useI18n();
  const { currentBizId } = useGlobalBizs();

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isShowBatchEntry = ref(false);
  const isSubmitting = ref(false);

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);
  const selectedIps = shallowRef<InstanceSelectorValues<TendbhaInstanceModel>>({ [ClusterTypes.TENDBHA]: [] });

  const formData = reactive({
    is_check_process: true,
    is_verify_checksum: true,
    is_check_delay: true,
  });

  const tabListConfig = {
    [ClusterTypes.TENDBHA]: [
      {
        name: t('故障主库主机'),
      },
    ],
  } as unknown as Record<ClusterTypes, PanelListType>;

  let ipMemo = {} as Record<string, boolean>;

  // 批量录入
  const handleShowBatchEntry = () => {
    isShowBatchEntry.value = true;
  };
  // 批量录入
  const handleBatchEntry = (list: Array<IBatchEntryValue>) => {
    const newList = list.map((item) => createRowData(item));
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
  const handelMasterProxyChange = (data: InstanceSelectorValues<TendbhaInstanceModel>) => {
    selectedIps.value = data;
    const newList = [] as IDataRow[];
    data.tendbha.forEach((proxyData) => {
      const { ip, bk_host_id, bk_cloud_id } = proxyData;
      if (!ipMemo[ip]) {
        newList.push(
          createRowData({
            masterData: {
              bk_host_id,
              bk_cloud_id,
              ip,
            },
          }),
        );
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
    const ip = tableData.value[index].masterData?.ip;
    if (ip) {
      delete ipMemo[ip];
      const clustersArr = selectedIps.value[ClusterTypes.TENDBHA];
      selectedIps.value[ClusterTypes.TENDBHA] = clustersArr.filter((item) => item.ip !== ip);
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
          ticket_type: 'MYSQL_MASTER_SLAVE_SWITCH',
          remark: '',
          details: {
            ...formData,
            infos: data,
          },
          bk_biz_id: currentBizId,
        }).then((data) => {
          window.changeConfirm = false;

          router.push({
            name: 'MySQLMasterSlaveSwap',
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
    ipMemo = {};
    selectedIps.value[ClusterTypes.TENDBHA] = [];
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .mysql-master-slave-swap-page {
    padding-bottom: 20px;

    .item-block {
      margin-top: 24px;
    }

    .page-action-box {
      display: flex;
      align-items: center;
      margin-top: 16px;
    }
  }
</style>
