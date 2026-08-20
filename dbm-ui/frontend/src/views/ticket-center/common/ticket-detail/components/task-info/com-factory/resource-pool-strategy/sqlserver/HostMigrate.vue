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
    row-key="origin_ip">
    <TicketInfoTableColumn
      col-key="origin_ip"
      :get-copy-value="(item: RowData) => item.origin_ip?.ip || ''"
      :min-width="260"
      :title="t('目标主机')">
      <template #default="{ row }: { row: RowData }">
        {{ row.origin_ip.ip }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="related_cluster_infos"
      :get-copy-value="
        (item: RowData) =>
          item.cluster_ids.map((clusterId) => ticketDetails.details.clusters?.[clusterId]?.immute_domain || '')
      "
      :min-width="260"
      :title="t('关联集群实例')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="item in row.related_cluster_infos"
          :key="item.instance_address"
          style="line-height: 20px">
          <p>
            {{ item.master_domain }}
          </p>
          <p style="color: #979ba5">-- {{ item.instance_address }}</p>
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec_id"
      :min-width="120"
      :title="t('规格')">
      <template #default="{ row }: { row: RowData }">
        <span v-if="row.resource_spec.new_hosts">
          {{ ticketDetails.details.specs?.[row.resource_spec.new_hosts?.spec_id]?.name || '--' }}
        </span>
        <span v-else-if="row.resource_spec.backend_group">
          {{ ticketDetails.details.specs?.[row.resource_spec.backend_group?.spec_id]?.name || '--' }}
        </span>
        <span v-else> -- </span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row }: { row: RowData }">
        <template v-if="row.resource_spec.new_hosts?.label_names?.length">
          <DbTag
            v-for="item in row.resource_spec.new_hosts.label_names"
            :key="item">
            {{ item }}
          </DbTag>
        </template>
        <template v-else-if="row.resource_spec.backend_group?.label_names?.length">
          <DbTag
            v-for="item in row.resource_spec.backend_group.label_names"
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
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.ResourcePool.HostMigrate>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.SQLSERVER_HOST_MIGRATE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
