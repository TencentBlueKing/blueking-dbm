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
  <BkTable :data="ticketDetails.details.infos">
    <BkTableColumn :label="t('目标集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="from_database"
      :label="t('同步 DB')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="dbName in data.sync_dbs"
          :key="dbName">
          {{ dbName }}
        </BkTag>
        <span v-if="data.sync_dbs.length < 1">--</span>
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.BuildDbSync>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();
  defineOptions({
    name: TicketTypes.SQLSERVER_BUILD_DB_SYNC,
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
