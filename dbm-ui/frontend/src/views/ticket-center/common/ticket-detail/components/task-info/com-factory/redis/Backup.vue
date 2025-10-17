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
  <PrimaryTable
    :data="ticketDetails.details.rules"
    row-key="cluster_id">
    <TableColumn
      col-key="cluster_id"
      :min-width="220"
      :title="t('集群')">
      <template #default="{ row }: { row: IRowData }">
        {{ ticketDetails.details.clusters[row.cluster_id]?.immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="cluster_type_name"
      :title="t('架构版本')"
      :width="200">
      <template #default="{ row }: { row: IRowData }">
        {{ ticketDetails.details.clusters[row.cluster_id]?.cluster_type_name }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="target"
      :min-width="130"
      :title="t('备份目标')" />
    <TableColumn
      col-key="backup_type"
      :min-width="130"
      :title="t('备份保存时间')">
      <template #default="{ row }: { row: IRowData }">
        {{ backupTypeMap[row.backup_type as keyof typeof backupTypeMap] }}
      </template>
    </TableColumn>
  </PrimaryTable>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.Backup>;
  }

  type IRowData = Props['ticketDetails']['details']['rules'][number];

  defineOptions({
    name: TicketTypes.REDIS_BACKUP,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const backupTypeMap = {
    forever_backup: t('3年'),
    normal_backup: t('1个月'),
  };
</script>
