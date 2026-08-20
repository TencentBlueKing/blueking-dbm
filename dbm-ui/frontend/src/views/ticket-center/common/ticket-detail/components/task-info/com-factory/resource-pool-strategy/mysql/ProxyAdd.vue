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
        (item: RowData) => item.cluster_ids.map((clusterId) => ticketDetails.details.clusters[clusterId].immute_domain)
      "
      :min-width="250"
      :title="t('目标集群')">
      <template #default="{ row: data }: { row: RowData }">
        <p
          v-for="clusterId in data.cluster_ids"
          :key="clusterId">
          {{ ticketDetails.details.clusters[clusterId].immute_domain }}
        </p>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="current_proxy_num"
      :min-width="120"
      :title="t('当前数量（台）')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data?.current_proxy_num || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="resource_spec.new_proxies.count"
      :min-width="120"
      :title="t('扩容数量（台）')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.resource_spec.new_proxies?.count || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="current_proxy_num"
      :min-width="120"
      :title="t('最终数量（台）')">
      <template #default="{ row: data }: { row: RowData }">
        {{
          data?.current_proxy_num && data.resource_spec.new_proxies?.count
            ? data.current_proxy_num + data.resource_spec.new_proxies.count
            : '--'
        }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec_id"
      :min-width="120"
      :title="t('规格')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.specs?.[data.resource_spec.new_proxies.spec_id]?.name || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row: data }: { row: RowData }">
        <template v-if="data.resource_spec.new_proxies?.label_names?.length">
          <DbTag
            v-for="item in data.resource_spec.new_proxies.label_names"
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

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.ProxyAdd>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_PROXY_ADD,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
