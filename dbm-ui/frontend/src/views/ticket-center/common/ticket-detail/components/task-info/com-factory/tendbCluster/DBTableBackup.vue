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
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="cluster_id"
      fixed="left"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.cluster_id].immute_domain"
      :title="t('目标集群')"
      :width="200">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spider_mnt_address"
      :min-width="120"
      :title="t('备份位置')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.spider_mnt_address || 'RemoteDR' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="db_patterns"
      :min-width="120"
      :title="t('备份DB名')">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.db_patterns" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="ignore_dbs"
      :min-width="120"
      :title="t('忽略DB名')">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.ignore_dbs" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="table_patterns"
      :min-width="120"
      :title="t('备份表名')">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.table_patterns" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="ignore_tables"
      :min-width="120"
      :title="t('忽略表名')">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.ignore_tables" />
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.DbTableBackup>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_DB_TABLE_BACKUP,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
