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
    row-key="new_proxy.ip">
    <TableColumn
      :min-width="250"
      :title="t('目标集群')">
      <template #default="{ row: data }: { row: RowData }">
        <div
          v-for="clusterId in data.cluster_ids"
          :key="clusterId"
          style="line-height: 20px">
          {{ ticketDetails.details.clusters[clusterId].immute_domain }}
        </div>
      </template>
    </TableColumn>
    <TableColumn :title="t('新Proxy主机')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.new_proxy.ip }}
      </template>
    </TableColumn>
  </PrimaryTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mysql.ProxyAdd>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_PROXY_ADD,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
