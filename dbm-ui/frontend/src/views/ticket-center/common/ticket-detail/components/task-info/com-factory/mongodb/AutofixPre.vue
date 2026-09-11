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
    :data="ticketDetails.details.infos"
    row-key="autofix_core_id">
    <TicketInfoTableColumn
      col-key="ip"
      :get-copy-value="(row: RowData) => `${row.ip}:${(row.ports || []).join(',')}`"
      :title="t('故障实例')"
      width="220">
      <template #default="{ row }: { row: RowData }">
        {{ row.ip }}:{{ (row.ports || []).join(',') || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="immute_domain"
      :get-copy-value="(row: RowData) => row.immute_domain"
      :title="t('所属集群')">
      <template #default="{ row }: { row: RowData }">
        <p>{{ row.immute_domain || '--' }}</p>
        <p style="color: #979ba5">
          {{ clusterTypeName(row) }}
        </p>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="bk_host_id"
      :title="t('主机ID')"
      width="100">
      <template #default="{ row }: { row: RowData }">
        {{ row.bk_host_id || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="autofix_core_id"
      :title="t('自愈待办ID')"
      width="120">
      <template #default="{ row }: { row: RowData }">
        {{ row.autofix_core_id || '--' }}
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  type RowData = Mongodb.AutofixPre['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Mongodb.AutofixPre>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_AUTOFIX_PRE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const clusterTypeName = (row: RowData) => {
    const clusterId = row.cluster_ids?.[0];
    if (clusterId && props.ticketDetails.details.clusters?.[clusterId]) {
      return props.ticketDetails.details.clusters[clusterId].cluster_type_name || row.cluster_type || '--';
    }
    return row.cluster_type || '--';
  };
</script>
