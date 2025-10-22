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
    :data="ticketDetails.details.infos"
    row-key="cluster_ids">
    <TableColumn
      col-key="cluster_ids"
      fixed="left"
      :min-width="250"
      :title="t('目标集群')">
      <template #default="{ row }: { row : RowData }">
        <template v-if="row.cluster_ids">
          <div
            v-for="clusterId in row.cluster_ids"
            :key="clusterId">
            {{ ticketDetails.details.clusters[clusterId].immute_domain }}
          </div>
        </template>
        <span v-else>
          {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
        </span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="cluster_id"
      :title="t('架构版本')"
      :width="200">
      <template #default="{ row }: { row : RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].cluster_type_name }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="current_versions"
      :min-width="250"
      :title="t('当前版本')">
      <template #default="{ row }: { row : RowData }">
        <div
          v-for="item in row.current_versions"
          :key="item">
          {{ item }}
        </div>
      </template>
    </TableColumn>
    <TableColumn
      col-key="target_versions"
      :min-width="250"
      :title="t('目标版本')">
      <template #default="{ row }: { row : RowData }">
        {{ row.target_version ? row.target_version : row.target_versions[0].version }}
      </template>
    </TableColumn>
  </PrimaryTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  type RowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Redis.VersionUpdateOnline>;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
