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
    ellipsis
    row-key="cluster_id">
    <TableColumn :title="t('目标集群')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="from_database"
      :title="t('原 DB 名')">
      <template #default="{ row: data }: { row: RowData }">
        <BkTag v-if="data">
          {{ data.from_database }}
        </BkTag>
      </template>
    </TableColumn>
    <TableColumn
      col-key="to_database"
      :title="t('新 DB 名')">
      <template #default="{ row: data }: { row: RowData }">
        <BkTag v-if="data">
          {{ data.to_database }}
        </BkTag>
      </template>
    </TableColumn>
  </PrimaryTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.DbRename>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.SQLSERVER_DBRENAME,
    inheritAttrs: false,
  });
  defineProps<Props>();
  const { t } = useI18n();
</script>
