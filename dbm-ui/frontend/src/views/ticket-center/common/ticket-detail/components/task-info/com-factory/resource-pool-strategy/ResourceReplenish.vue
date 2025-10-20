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
  <TicketInfoTable
    :data="[ticketDetails.details]"
    row-key="db_type">
    <TicketInfoTableColumn
      col-key="db_type"
      :min-width="150"
      :title="t('DB 类型')">
      <template #default="{ row: data }: { row: RowData }">
        {{ dbNameMap[data.db_type] || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec.spec_machine_type"
      :min-width="150"
      :title="t('规格类型')">
      <template #default="{ row: data }: { row: RowData }">
        {{ machineTypeMap[data.spec?.spec_machine_type] || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec.spec_name"
      :min-width="200"
      :title="t('规格')">
      <template #default="{ row: data }: { row: RowData }"> {{ data.spec?.spec_name || '--' }} </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="city"
      :min-width="120"
      :title="t('地域')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.city || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="subzone"
      :min-width="120"
      :title="t('园区')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.subzone || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="os_name"
      :min-width="120"
      :title="t('操作系统')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.os_name || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="count"
      :min-width="120"
      :title="t('申请数量')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.count || '--' }}
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type ResourcePool } from '@services/model/ticket/ticket';

  import { DBTypeInfos, TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<ResourcePool.ResourcePoolReplenish>;
  }

  type RowData = Props['ticketDetails']['details'];

  defineOptions({
    name: TicketTypes.RESOURCE_HCM_REPLENISH,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const dbNameMap: Record<string, string> = {};
  const machineTypeMap: Record<string, string> = {};
  Object.values(DBTypeInfos).forEach((db) => {
    dbNameMap[db.id] = db.name;
    db.machineList.forEach((machine) => {
      machineTypeMap[`${machine.value}`] = `${machine.label}`;
    });
  });
</script>
