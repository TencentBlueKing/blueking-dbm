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
    row-key="source_cluster_id">
    <TicketInfoTableColumn
      col-key="source_root_id"
      :min-width="180"
      :title="t('失败 DTS root_id')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.source_root_id || row.source_root_id || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="source_cluster_id"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.source_cluster_id].immute_domain"
      :min-width="280"
      :title="t('源集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.source_cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="target_cluster_id"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.target_cluster_id].immute_domain"
      :min-width="280"
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.target_cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="exec_host"
      :min-width="160"
      :title="t('执行机')">
      <template #default="{ row }: { row: RowData }">
        <span v-if="row.exec_host_id">#{{ row.exec_host_id }}</span>
        <span v-else-if="row.exec_host?.ip">{{ row.exec_host.ip }}</span>
        <span v-else>--</span>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  type RowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Mongodb.DtsCleanup>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_DTS_CLEANUP,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
