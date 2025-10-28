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
    :data="[ticketDetails]"
    row-key="cluster_id">
    <InfoTableColumn
      col-key="cluster_id"
      :get-copy-value="(item: RowData) => ticketDetails.details.clusters[item.id].immute_domain"
      :title="t('集群')">
      <template #default="{ row }: { row: RowData }">
        {{ row.details.clusters[row.details.cluster_id].immute_domain }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="cluster_type_name"
      :title="t('集群类型')">
      <template #default="{ row }: { row: RowData }">
        {{ row.details.clusters[row.details.cluster_id].cluster_type_name }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      v-if="ticketDetails.details.spider_role"
      col-key="role"
      :title="t('角色')">
      <template #default="{ row }: { row: RowData }">
        {{ RoleDisplayMap[row.details.spider_role!] }}
      </template>
    </InfoTableColumn>
  </InfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { DetailClusters } from '@services/model/ticket/details/common';
  import TicketModel from '@services/model/ticket/ticket';

  import InfoTable, { InfoTableColumn } from '../components/info-table/Index.vue';

  interface Props {
    ticketDetails: TicketModel<{
      cluster_id: number;
      clusters: DetailClusters;
      spider_role?: string;
    }>;
  }

  type RowData = Props['ticketDetails'];

  defineProps<Props>();

  const { t } = useI18n();

  const RoleDisplayMap: Record<string, string> = {
    spider_master: 'Spider Master',
    spider_slave: 'Spider Slave',
  };
</script>
