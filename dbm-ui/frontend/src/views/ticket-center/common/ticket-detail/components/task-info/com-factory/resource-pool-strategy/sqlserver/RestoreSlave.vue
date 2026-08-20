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
    row-key="cluster_ids">
    <TicketInfoTableColumn
      col-key="cluster_ids"
      :get-copy-value="
        (row: RowData) => row.old_nodes.old_slave_host[0].ip
      "
      :title="t('待重建从库主机')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.old_nodes.old_slave_host[0].ip }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="immute_domain"
      :title="t('同机关联集群')">
      <template #default="{ row: data }: { row: RowData }">
        <div
          v-for="clusterId in data.cluster_ids"
          :key="clusterId"
          style="line-height: 20px">
          {{ ticketDetails.details.clusters[clusterId].immute_domain }}
        </div>
      </template>
    </TicketInfoTableColumn>
    <template v-if="isResourcePool">
      <TicketInfoTableColumn
        col-key="spec_id"
        :min-width="120"
        :title="t('规格')">
        <template #default="{ row: data }: { row: RowData }">
          {{ ticketDetails.details.specs?.[data.resource_spec.sqlserver_ha?.spec_id]?.name || '--' }}
        </template>
      </TicketInfoTableColumn>
      <TicketInfoTableColumn
        col-key="label_names"
        :min-width="200"
        :title="t('资源标签')">
        <template #default="{ row: data }: { row: RowData }">
          <template v-if="data.resource_spec.sqlserver_ha?.label_names?.length">
            <DbTag
              v-for="item in data.resource_spec.sqlserver_ha.label_names"
              :key="item">
              {{ item }}
            </DbTag>
          </template>
          <DbTag
            v-else
            theme="success">
            {{ t('通用无标签') }}
          </DbTag>
        </template>
      </TicketInfoTableColumn>
    </template>
    <TicketInfoTableColumn
      v-else
      col-key="sqlserver_ha"
      :title="t('新从库主机')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.resource_spec.sqlserver_ha.hosts[0].ip }}
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.ResourcePool.RestoreSlave>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.SQLSERVER_RESTORE_SLAVE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isResourcePool = !props.ticketDetails.details.infos[0].resource_spec.sqlserver_ha.hosts;
</script>
