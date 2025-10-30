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
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="cluster_id"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.cluster_id].immute_domain"
      :min-width="250"
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_type_name"
      :title="t('架构版本')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].cluster_type_name }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="node_type"
      :title="t('缩容节点类型')">
      Proxy
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="proxy_reduced_hosts"
      :title="t('主机选择方式')">
      <template #default="{ row }: { row: RowData }">
        {{
          row.proxy_reduced_hosts?.length ? row.proxy_reduced_hosts.map((item) => item.ip).join('\n') : t('自动匹配')
        }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="target_proxy_count"
      :title="t('缩容数量(台)')">
      <template #default="{ row }: { row: RowData }">
        {{ row.target_proxy_count }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="online_switch_type"
      :title="t('切换模式')">
      <template #default="{ row }: { row: RowData }">
        {{ switchModeMap[row.online_switch_type] }}
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.ProxyScaleDown>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.REDIS_PROXY_SCALE_DOWN,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const switchModeMap = {
    no_confirm: t('无需确认'),
    user_confirm: t('人工确认'),
  };
</script>
