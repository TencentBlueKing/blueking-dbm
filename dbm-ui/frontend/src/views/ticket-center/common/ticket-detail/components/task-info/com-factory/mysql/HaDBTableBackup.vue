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
  <InfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_id">
    <InfoTableColumn
      col-key="cluster_id"
      :get-copy-value="(item: RowData) => ticketDetails.details.clusters[item.cluster_id].immute_domain"
      :title="t('目标集群')"
      :width="240">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="backup_on"
      :title="t('备份位置')"
      :width="180">
      <template #default="{ row }: { row: RowData }">
        {{
          ticketDetails.details.clusters[row.cluster_id]
            ? ticketDetails.details.clusters[row.cluster_id].cluster_type === ClusterTypes.TENDBHA
              ? 'Slave'
              : 'Master'
            : '--'
        }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="db_patterns"
      :title="t('备份DB名')"
      :width="180">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.db_patterns" />
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="ignore_dbs"
      :title="t('忽略DB名')"
      :width="180">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ignore_dbs" />
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="table_patterns"
      :title="t('备份表名')"
      :width="180">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.table_patterns" />
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="ignore_tables"
      :title="t('忽略表名')"
      :width="180">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ignore_tables" />
      </template>
    </InfoTableColumn>
  </InfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import InfoTable, { InfoTableColumn } from '../components/info-table/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.HaDBTableBackup>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_HA_DB_TABLE_BACKUP,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
