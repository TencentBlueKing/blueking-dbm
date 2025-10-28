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
      :min-width="220"
      :title="t('集群')">
      <template #default="{ row:data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="host_source"
      :title="t('主机来源')">
      <template #default>
        {{ t('业务空闲机') }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="rollback_host"
      :title="t('回档新主机')">
      <template #default="{ row:data }: { row: RowData }">
        {{ data.rollback_host.ip }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="backup_source"
      :min-width="150"
      :title="t('备份源')">
      <template #default="{ row:data }: { row: RowData }">
        {{ backupSourceMap[data.backup_source as keyof typeof backupSourceMap] }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="rollback_time"
      :title="t('回档类型')">
      <template #default="{ row:data }: { row: RowData }">
        <span v-if="data.rollback_time">{{ t('回档到指定时间') }} - {{ utcDisplayTime(data.rollback_time) }}</span>
        <span v-else-if="data.backupinfo.backup_time && data.backupinfo.mysql_role">
          {{ t('备份记录') }} - {{ data.backupinfo?.mysql_role }}
          {{ utcDisplayTime(data.backupinfo?.backup_time) }}
        </span>
        <span v-else>--</span>
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="databases"
      :title="t('回档DB名')">
      <template #default="{ row:data }: { row: RowData }">
        <TagBlock :data="data.databases" />
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="databases_ignore"
      :title="t('忽略DB名')">
      <template #default="{ row:data }: { row: RowData }">
        <TagBlock :data="data.databases_ignore" />
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="tables"
      :title="t('回档表名')">
      <template #default="{ row:data }: { row: RowData }">
        <TagBlock :data="data.tables" />
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="tables_ignore"
      :title="t('忽略表名')">
      <template #default="{ row:data }: { row: RowData }">
        <TagBlock :data="data.tables_ignore" />
      </template>
    </InfoTableColumn>
  </InfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import TagBlock from '@components/tag-block/Index.vue';

  import { utcDisplayTime } from '@utils';

  import InfoTable, { InfoTableColumn } from '../../../components/info-table/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.RollbackCluster>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  const { t } = useI18n();

  const backupSourceMap = {
    local: t('本地备份'),
    remote: t('远程备份'),
  };
</script>
