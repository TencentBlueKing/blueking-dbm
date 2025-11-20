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
    :data="ticketDetails.details.rules"
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="cluster_id"
      :get-copy-value="(row: IRowData) => ticketDetails.details.clusters[row.cluster_id].immute_domain"
      :min-width="220"
      :title="t('集群')">
      <template #default="{ row }: { row: IRowData }">
        {{ ticketDetails.details.clusters[row.cluster_id]?.immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_type_name"
      :title="t('架构版本')"
      :width="200">
      <template #default="{ row }: { row: IRowData }">
        {{ ticketDetails.details.clusters[row.cluster_id]?.cluster_type_name }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="backup"
      :title="t('清档前备份')">
      <template #default="{ row }: { row: IRowData }">
        <span>{{ row.backup ? t('是') : t('否') }}</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="force"
      :title="t('强制清档')">
      <template #default="{ row }: { row: IRowData }">
        <span>{{ row.force ? t('是') : t('否') }}</span>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.Purge>;
  }

  defineOptions({
    name: TicketTypes.REDIS_PURGE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  type IRowData = Props['ticketDetails']['details']['rules'][number];

  const { t } = useI18n();
</script>
