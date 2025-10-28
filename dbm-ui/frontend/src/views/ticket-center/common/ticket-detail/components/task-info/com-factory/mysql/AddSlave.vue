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
    :data="ticketDetails.details.infos"
    row-key="new_slave.ip">
    <InfoTableColumn
      col-key="cluster_ids"
      :get-copy-value="
        (item: RowData) => item.cluster_ids.map((clusterId) => ticketDetails.details.clusters[clusterId].immute_domain)
      "
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="clusterId in row.cluster_ids"
          :key="clusterId"
          style="line-height: 20px">
          {{ ticketDetails.details.clusters[clusterId].immute_domain }}
        </div>
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="new_slave"
      :title="t('新从库主机')">
      <template #default="{ row }: { row: RowData }">
        {{ row.new_slave.ip }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="backup_source"
      :title="t('备份源')">
      <template #default>
        {{ ticketDetails.details.backup_source === 'local' ? t('本地备份') : t('远程备份') }}
      </template>
    </InfoTableColumn>
  </InfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoTable, { InfoTableColumn } from '../components/info-table/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.AddSlave>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_ADD_SLAVE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
