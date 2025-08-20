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
  <!-- <PrimaryTable
    :columns="columns"
    :data="ticketDetails.details.rules"
    row-key="cluster_id" /> -->
  <PrimaryTable
    :columns="columns"
    :data="ticketDetails.details.rules"
    row-key="cluster_id">
    <template #immute-domain="{ row }: { row: IRowData }">
      {{ ticketDetails.details.clusters[row.cluster_id]?.immute_domain }}
    </template>
    <template #cluster-type-name="{ row }: { row: IRowData }">
      {{ ticketDetails.details.clusters[row.cluster_id]?.cluster_type_name }}
    </template>
    <template #backup-type="{ row }: { row: IRowData }">
      {{ backupTypeMap[row.backup_type as keyof typeof backupTypeMap] }}
    </template>
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

  const columns = [
    {
      cell: 'immute-domain',
      minWidth: 220,
      title: t('集群'),
    },
    {
      cell: 'cluster-type-name',
      title: t('架构版本'),
      width: 200,
    },
    {
      colKey: 'target',
      minWidth: 130,
      title: t('备份目标'),
    },
    {
      cell: 'backup-type',
      minWidth: 130,
      title: t('备份保存时间'),
    },
  ];
</script>
