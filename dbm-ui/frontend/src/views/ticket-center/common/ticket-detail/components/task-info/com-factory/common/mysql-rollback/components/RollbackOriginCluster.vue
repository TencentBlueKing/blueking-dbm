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
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.cluster_id].immute_domain"
      :min-width="220"
      :title="t('集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <slot />
    <TicketInfoTableColumn
      col-key="backup_source"
      :min-width="150"
      :title="t('备份源')">
      <template #default="{ row }: { row: RowData }">
        {{ backupSourceMap[row.backup_source as keyof typeof backupSourceMap] }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="rollback_time"
      :title="t('回档类型')">
      <template #default="{ row }: { row: RowData }">
        <span v-if="row.rollback_time">{{ t('回档到指定时间') }} - {{ utcDisplayTime(row.rollback_time) }}</span>
        <span v-else-if="row.backupinfo.backup_time && row.backupinfo.mysql_role">
          {{ t('备份记录') }} - {{ row.backupinfo?.mysql_role }}
          {{ utcDisplayTime(row.backupinfo?.backup_time) }}
        </span>
        <span v-else>--</span>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { utcDisplayTime } from '@utils';

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
