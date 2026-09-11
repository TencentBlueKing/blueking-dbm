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
    row-key="immute_domain">
    <TicketInfoTableColumn
      col-key="immute_domain"
      :get-copy-value="(row: RowData) => row.immute_domain"
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        <p>{{ row.immute_domain || '--' }}</p>
        <p style="color: #979ba5">
          {{ row.cluster_type || '--' }}
        </p>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="mongod_list"
      :title="t('故障 mongod')">
      <template #default="{ row }: { row: RowData }">
        <p
          v-for="item in row.mongod_list || []"
          :key="item.ip">
          {{ item.ip }}
        </p>
        <span v-if="!(row.mongod_list || []).length">--</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="mongos_list"
      :title="t('故障 mongos')">
      <template #default="{ row }: { row: RowData }">
        <p
          v-for="item in row.mongos_list || []"
          :key="item.ip">
          {{ item.ip }}
        </p>
        <span v-if="!(row.mongos_list || []).length">--</span>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  type RowData = Mongodb.Autofix['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Mongodb.Autofix>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_AUTOFIX,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
