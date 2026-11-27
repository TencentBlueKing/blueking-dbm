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
    row-key="target_cluster_id">
    <TicketInfoTableColumn
      col-key="source_mode"
      :title="t('数据源')"
      :width="140">
      <template #default="{ row }: { row: RowData }">
        <div>{{ row.source_mode === 'backup_ticket' ? t('备份单据') : t('在线集群') }}</div>
        <div v-if="row.backup_ticket_id">#{{ row.backup_ticket_id }}</div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="source_cluster_id"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.source_cluster_id].immute_domain"
      :min-width="220"
      :title="t('源集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.source_cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="target_cluster_id"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.target_cluster_id].immute_domain"
      :min-width="220"
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.target_cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="db_patterns"
      :min-width="220"
      :title="t('库表范围')">
      <template #default="{ row }: { row: RowData }">
        <div class="ns-filter-line">
          <span>{{ t('DB') }}</span>
          <TagBlock :data="row.ns_filter?.db_patterns || []" />
        </div>
        <div
          v-if="row.ns_filter?.ignore_dbs?.length"
          class="ns-filter-line">
          <span>{{ t('忽略 DB') }}</span>
          <TagBlock :data="row.ns_filter.ignore_dbs" />
        </div>
        <div class="ns-filter-line">
          <span>{{ t('表') }}</span>
          <TagBlock :data="row.ns_filter?.table_patterns || []" />
        </div>
        <div
          v-if="row.ns_filter?.ignore_tables?.length"
          class="ns-filter-line">
          <span>{{ t('忽略表') }}</span>
          <TagBlock :data="row.ns_filter.ignore_tables" />
        </div>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  type RowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Mongodb.DataMigrate>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_DATA_MIGRATE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>

<style lang="less" scoped>
  .ns-filter-line {
    display: flex;
    align-items: flex-start;
    gap: 8px;

    > span {
      flex: none;
      line-height: 22px;
      color: #979ba5;
    }
  }
</style>
