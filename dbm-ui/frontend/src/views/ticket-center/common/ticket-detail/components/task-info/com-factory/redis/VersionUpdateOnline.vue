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
    :data="dataList"
    row-key="cluster_id">
    <TableColumn
      fixed="left"
      :min-width="250"
      :title="t('源集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      :title="t('架构版本')"
      :width="200">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].cluster_type_name }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="node_type"
      :title="t('节点类型')"
      :width="150">
    </TableColumn>
    <TableColumn
      :min-width="250"
      :title="t('当前使用的版本')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="item in row.current_versions"
          :key="item">
          {{ item }}
        </div>
      </template>
    </TableColumn>
    <TableColumn
      col-key="target_version"
      :min-width="250"
      :title="t('目标版本')">
    </TableColumn>
  </PrimaryTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  type RowData = { cluster_id: number } & Omit<Props['ticketDetails']['details']['infos'][number], 'cluster_ids'>;

  interface Props {
    ticketDetails: TicketModel<Redis.VersionUpdateOnline>;
  }

  defineOptions({
    name: TicketTypes.REDIS_VERSION_UPDATE_ONLINE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const dataList: RowData[] = props.ticketDetails.details.infos.flatMap((infoItem) =>
    infoItem.cluster_ids.map((clusterId) => ({
      ...infoItem,
      cluster_id: clusterId,
    })),
  );
</script>
