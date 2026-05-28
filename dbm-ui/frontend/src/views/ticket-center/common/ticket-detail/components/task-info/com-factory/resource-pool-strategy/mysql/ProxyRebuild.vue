<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="rebuild_proxy_hosts"
      :get-copy-value="(row: RowData) => (row.rebuild_proxy_hosts || []).map((item) => item.ip)"
      :min-width="180"
      :title="t('目标 Proxy 实例')">
      <template #default="{ row: data }: { row: RowData }">
        <span v-if="!data.rebuild_proxy_hosts?.length">--</span>
        <p
          v-for="item in data.rebuild_proxy_hosts"
          v-else
          :key="item.ip">
          {{ item.ip }}
        </p>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_id"
      :min-width="220"
      :title="t('所属集群')">
      <template #default="{ row: data }: { row: RowData }">
        <span>{{ ticketDetails.details.clusters?.[data.cluster_id]?.immute_domain || '--' }}</span>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.ProxyRebuild>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_PROXY_REBUILD,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
