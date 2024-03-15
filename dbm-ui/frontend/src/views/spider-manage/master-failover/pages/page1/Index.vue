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
    <div class="spider-manage-master-failover-page">
      <BkAlert
        closable
        theme="info"
        :title="t('主库故障切换：Slave 提升成主库，断开同步，切换后集群成单节点状态，一般用于紧急切换')" />
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
        v-model:isShow="isShowMasterInstanceSelector"
        :cluster-types="[ClusterTypes.TENDBCLUSTER]"
        :selected="selectedIps"
        @change="handelMasterProxyChange" />
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
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import { createTicket } from '@services/source/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import InstanceSelector, { type InstanceSelectorValues, type IValue } from '@components/instance-selector/Index.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

  const { t } = useI18n();
  const router = useRouter();
  const { currentBizId } = useGlobalBizs();

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting = ref(false);

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);
  const selectedIps = shallowRef<InstanceSelectorValues<IValue>>({ tendbcluster: [] });

  const formData = reactive({
    is_check_process: false,
    is_verify_checksum: false,
    is_check_delay: false,
  });

  let ipMemo = {} as Record<string, boolean>;

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.masterData && !firstRow.slaveData && !firstRow.clusterData;
  };

  // Master 批量选择
  const handleShowMasterBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };

  // Master 批量选择
  const handelMasterProxyChange = (data: InstanceSelectorValues<IValue>) => {
    selectedIps.value = data;
    const newList = data.tendbcluster.reduce((result, item) => {
      const { bk_host_id, bk_cloud_id, instance_address: instanceAddress } = item;
      const [ip] = instanceAddress.split(':');
      if (!ipMemo[ip]) {
        const row = createRowData({
          masterData: {
            bk_host_id,
            bk_cloud_id,
            ip,
          },
        });
        result.push(row);
        ipMemo[ip] = true;
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

  // 追加一个集群
  const handleAppend = (index: number, appendList: Array<IDataRow>) => {
    const dataList = [...tableData.value];
    dataList.splice(index + 1, 0, ...appendList);
    tableData.value = dataList;
  };

  // 删除一个集群
  const handleRemove = (index: number) => {
    const dataList = [...tableData.value];
    const ip = dataList[index].masterData?.ip;
    dataList.splice(index, 1);
    tableData.value = dataList;
    if (ip) {
      delete ipMemo[ip];
      const clustersArr = selectedIps.value.tendbcluster;
      selectedIps.value.tendbcluster = clustersArr.filter((item) => item.ip !== ip);
    }
  };

  const handleSubmit = () => {
    isSubmitting.value = true;
    Promise.all(rowRefs.value.map((item: { getValue: () => Promise<any> }) => item.getValue()))
      .then((data) =>
        createTicket({
          ticket_type: TicketTypes.TENDBCLUSTER_MASTER_FAIL_OVER,
          remark: '',
          details: {
            ...formData,
            infos: data,
          },
          bk_biz_id: currentBizId,
        }).then((data) => {
          window.changeConfirm = false;

          router.push({
            name: 'spiderMasterFailover',
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
    selectedIps.value.tendbcluster = [];
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .spider-manage-master-failover-page {
    padding-bottom: 20px;

    .item-block {
      margin-top: 24px;
    }
  }
</style>
