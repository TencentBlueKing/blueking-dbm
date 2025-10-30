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
    row-key="id">
    <TicketInfoTableColumn
      col-key="master.ip"
      :get-copy-value="(row: RowData) => row.master.ip"
      :title="t('故障主库主机')">
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="slave.ip"
      :title="t('从库主机')">
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="slave.ip"
      :title="t('同机关联的集群')">
      <template #default="{ row: data }: { row: RowData }">
        <div
          v-for="clusterId in data.cluster_ids"
          :key="clusterId"
          style="line-height: 20px">
          {{ ticketDetails.details.clusters[clusterId].immute_domain }}
        </div>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.MasterFailOver>;
  }

  defineOptions({
    name: TicketTypes.SQLSERVER_MASTER_FAIL_OVER,
    inheritAttrs: false,
  });

  defineProps<Props>();

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const { t } = useI18n();
</script>
