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
    <div class="sqlserver-master-slave-swap-page">
      <BkAlert
        closable
        theme="info"
        :title="t('主从互换：主机级别操作，即同机所有集群均会完成主从关系互切')" />
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
      <InstanceSelector
        v-model:is-show="isShowMasterInstanceSelector"
        :cluster-types="[ClusterTypes.SQLSERVER_HA]"
        :selected="instanceSelectValue"
        :tab-list-config="tabListConfig"
        @change="handelMasterProxyChange" />
    </div>
    <template #action>
      <BkButton
        class="w-88"
        :loading="isSubmitting"
        theme="primary"
        @click="handleSubmit">
        <DbIcon type="invisible1" />
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
  import { ref, shallowRef, type UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import SqlServerHaInstanceModel from '@services/model/sqlserver/sqlserver-ha-instance';
  import { getSqlServerInstanceList } from '@services/source/sqlserveHaCluster';
  import { createTicket } from '@services/source/ticket';

  import { useTicketCloneInfo } from '@hooks';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import InstanceSelector, { type PanelListType } from '@components/instance-selector/Index.vue';

  import RenderData from './components/RenderData/Index.vue';
  import RenderDataRow, { createRowData, type IDataRow } from './components/RenderData/Row.vue';

  // 检测列表是否为空
  const checkListEmpty = (list: Array<IDataRow>) => {
    if (list.length > 1) {
      return false;
    }
    const [firstRow] = list;
    return !firstRow.masterData && !firstRow.slaveData;
  };

  const tabListConfig = {
    [ClusterTypes.SQLSERVER_HA as string]: [
      {
        tableConfig: {
          getTableList: (params: ServiceParameters<typeof getSqlServerInstanceList>) =>
            getSqlServerInstanceList({
              ...params,
              role: 'backend_master',
            }),
        },
      },
    ],
  } as Record<string, PanelListType>;

  const router = useRouter();
  const { t } = useI18n();

  const rowRefs = ref();
  const isShowMasterInstanceSelector = ref(false);
  const isSubmitting = ref(false);
  const instanceSelectValue = shallowRef<Record<string, SqlServerHaInstanceModel[]>>({
    [ClusterTypes.SQLSERVER_HA]: [],
  });

  const tableData = shallowRef<Array<IDataRow>>([createRowData({})]);

  useTicketCloneInfo({
    type: TicketTypes.SQLSERVER_MASTER_SLAVE_SWITCH,
    onSuccess(cloneData) {
      tableData.value = cloneData.map((item) =>
        createRowData({
          masterData: {
            bk_host_id: item.master.bk_host_id,
            bk_cloud_id: item.master.bk_cloud_id,
            ip: item.master.ip,
          },
          slaveData: {
            bk_host_id: item.slave.bk_host_id,
            bk_cloud_id: item.slave.bk_cloud_id,
            ip: item.slave.ip,
          },
          clusterIdList: item.cluster_ids,
        }),
      );
    },
  });

  // Master 批量选择
  const handleShowMasterBatchSelector = () => {
    isShowMasterInstanceSelector.value = true;
  };
  // Master 批量选择
  const handelMasterProxyChange = (data: UnwrapRef<typeof instanceSelectValue>) => {
    instanceSelectValue.value = data;
    const newList = [] as IDataRow[];
    data[ClusterTypes.SQLSERVER_HA].forEach((proxyData) => {
      const { ip, bk_host_id, bk_cloud_id } = proxyData;
      newList.push(
        createRowData({
          masterData: {
            bk_host_id,
            bk_cloud_id,
            ip,
          },
        }),
      );
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
      .then((data) =>
        createTicket({
          ticket_type: TicketTypes.SQLSERVER_MASTER_SLAVE_SWITCH,
          remark: '',
          details: {
            infos: data,
          },
          bk_biz_id: window.PROJECT_CONFIG.BIZ_ID,
        }).then((data) => {
          window.changeConfirm = false;

          router.push({
            name: 'sqlServerMasterSlaveSwap',
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
    instanceSelectValue.value = {
      [ClusterTypes.SQLSERVER_HA]: [],
    };
    window.changeConfirm = false;
  };
</script>

<style lang="less">
  .sqlserver-master-slave-swap-page {
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
