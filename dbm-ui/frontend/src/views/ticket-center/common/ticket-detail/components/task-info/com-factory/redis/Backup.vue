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
  <BkTable :data="ticketDetails.details.rules">
    <BkTableColumn
      :label="t('集群')"
      :min-width="220">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('架构版本')"
      :min-width="130">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].cluster_type_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="target"
      :label="t('备份目标')"
      :min-width="130" />
    <BkTableColumn
      :label="t('备份类型')"
      :min-width="130">
      <template #default="{ data }: { data: RowData }">
        {{ backupTypeMap[data.backup_type] }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.Backup>;
  }

  type RowData = Props['ticketDetails']['details']['rules'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_BACKUP,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const backupTypeMap = {
    normal_backup: t('常规备份'),
    forever_backup: t('长期备份'),
  };
</script>
