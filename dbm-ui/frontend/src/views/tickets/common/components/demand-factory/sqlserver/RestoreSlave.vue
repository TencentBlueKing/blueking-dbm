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
    <BkTableColumn
      field="old_slave_host.ip"
      :label="t('待重建从库主机')" />
    <BkTableColumn
      field="new_cluster_name"
      :label="t('同机关联集群')">
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="clusterId in data.cluster_ids"
          :key="clusterId"
          style="line-height: 20px">
          {{ ticketDetails.details.clusters[clusterId].immute_domain }}
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="new_slave_host.ip"
      :label="t('新从库主机')" />
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.RestoreSlave>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.SQLSERVER_RESTORE_SLAVE,
  });

  const { t } = useI18n();
</script>
