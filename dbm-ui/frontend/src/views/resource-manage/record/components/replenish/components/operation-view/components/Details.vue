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
  <BkSideslider
    v-model:is-show="isShow"
    class="replenish-record-details-slider"
    :width="900">
    <template #header>
      <span>{{ t('操作详情') }}</span>
      <span class="header-desc">ID : {{ id }}</span>
    </template>
    <div class="replenish-record-details">
      <BkLoading :loading="isLoading">
        <BkTable
          border
          :data="tableData">
          <BkTableColumn
            field="spec_name"
            :label="t('规格')"
            :width="240">
            <template #default="{ row }: { row: RowData }">
              {{
                `${dbNameMap[row.db_type] || '--'} / ${machineTypeMap[row.spec?.spec_machine_type] || '--'} / ${row.spec?.spec_name || '--'}`
              }}
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="city"
            :label="t('地域')"
            :width="100">
            <template #default="{ row }: { row: RowData }">
              <span>{{ row.city }}</span>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="subzone"
            :label="t('园区')"
            :width="100">
            <template #default="{ row }: { row: RowData }">
              <span>{{ row.subzone }}</span>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="os_name"
            :label="t('操作系统')"
            :width="100">
            <template #default="{ row }: { row: RowData }">
              <span>{{ row.os_name }}</span>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="count"
            :label="t('补货数量')"
            :width="100">
            <template #default="{ row }: { row: RowData }">
              <span>{{ row.count }}</span>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="ticket_id"
            :label="t('关联补货单')"
            :width="100">
            <template #default="{ row }: { row: RowData }">
              <BkButton
                text
                theme="primary"
                @click="() => handleOpenBizTicket(row)">
                {{ row.ticket_id }}
              </BkButton>
            </template>
          </BkTableColumn>
          <BkTableColumn
            field="status"
            :label="t('操作结果')"
            :min-width="100">
            <template #default="{ row }: { row: RowData }">
              <DbIcon
                :class="{ 'rotate-loading': row.isRunning }"
                style="vertical-align: middle"
                svg
                :type="row.statusIcon" />
              <span class="ml-4">{{ row.statusText }}</span>
            </template>
          </BkTableColumn>
        </BkTable>
      </BkLoading>
    </div>
  </BkSideslider>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type ReplenishModel from '@services/model/db-resource/Replenish';
  import TicketModel from '@services/model/ticket/ticket';
  import { fetchReplenish } from '@services/source/dbresourceReplenish';
  import { getTicketDetails } from '@services/source/ticket';

  import { useSystemEnviron } from '@stores';

  import { DBTypeInfos } from '@common/const';

  type RowData = {
    isRunning: boolean;
    status: string;
    statusIcon: string;
    statusText: string;
    ticket_id: number;
  } & ReplenishModel;

  interface Props {
    id: number;
  }

  const props = defineProps<Props>();

  const isShow = defineModel<boolean>('isShow', {
    required: true,
  });

  const { t } = useI18n();
  const router = useRouter();
  const systemEnvironStore = useSystemEnviron();

  const tableData = shallowRef<RowData[]>([]);
  const isLoading = shallowRef(false);

  const dbNameMap: Record<string, string> = {};
  const machineTypeMap: Record<string, string> = {};
  Object.values(DBTypeInfos).forEach((db) => {
    dbNameMap[db.id] = db.name;
    db.machineList.forEach((machine) => {
      machineTypeMap[`${machine.value}`] = `${machine.label}`;
    });
  });

  const iconMap = {
    [TicketModel.STATUS_APPROVE]: 'sync-default',
    [TicketModel.STATUS_FAILED]: 'sync-failed',
    [TicketModel.STATUS_INNER_TODO]: 'sync-default',
    [TicketModel.STATUS_PENDING]: 'sync-default',
    [TicketModel.STATUS_RESOURCE_REPLENISH]: 'sync-default',
    [TicketModel.STATUS_REVOKED]: 'sync-failed',
    [TicketModel.STATUS_RUNNING]: 'sync-pending',
    [TicketModel.STATUS_SUCCEEDED]: 'sync-success',
    [TicketModel.STATUS_TERMINATED]: 'sync-failed',
    [TicketModel.STATUS_TIMER]: 'sync-pending',
    [TicketModel.STATUS_TODO]: 'sync-default',
  };

  const handleOpenBizTicket = (rowData: RowData) => {
    const path = router
      .resolve({
        name: 'bizTicketManage',
        params: {
          ticketId: rowData.ticket_id,
        },
      })
      .href.replace(/^\/(\d+)/, `${systemEnvironStore.urls.RESOURCE_INDEPENDENT_BIZ}`);

    window.open(`${window.location.origin}/${path}`, '_blank');
  };

  watch(
    isShow,
    async () => {
      if (isShow.value && props.id) {
        try {
          isLoading.value = true;
          const data = await fetchReplenish({
            id: props.id,
          });
          if (data.results.length === 0) {
            return;
          }

          const ticketInfos = await Promise.all(
            data.results[0].ticket_ids.map((id) =>
              getTicketDetails<TicketModel<ReplenishModel>>({
                id,
              }),
            ),
          );

          tableData.value = ticketInfos.map((item) => ({
            isRunning: iconMap[item.status] === 'sync-pending',
            status: item.status,
            statusIcon: iconMap[item.status],
            statusText: item.statusText,
            ticket_id: item.id,
            ...item.details,
          }));
        } finally {
          isLoading.value = false;
        }
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less">
  .replenish-record-details-slider {
    .header-desc {
      position: relative;
      display: flex;
      height: 22px;
      padding-left: 9px;
      margin-left: 16px;
      font-family: MicrosoftYaHei, sans-serif;
      font-size: 14px;
      line-height: 22px;
      letter-spacing: 0;
      color: #979ba5;

      &::before {
        position: absolute;
        top: 5px;
        left: 0;
        width: 1px;
        height: 14px;
        background-color: #979ba580;
        content: '';
      }
    }

    .replenish-record-details {
      margin: 18px 24px;
    }
  }
</style>
