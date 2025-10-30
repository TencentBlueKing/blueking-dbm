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
    class="details-backup__table"
    :data="tableData"
    row-key="immute_domain">
    <TicketInfoTableColumn
      col-key="immute_domain"
      ellipsis
      :get-copy-value="(row: RowData) => row.immute_domain"
      :title="t('目标集群')" />
    <TicketInfoTableColumn
      col-key="cluster_type"
      ellipsis
      :title="t('集群类型')" />
    <TicketInfoTableColumn
      col-key="current_nodes"
      ellipsis
      :title="t('当前Shard的节点数')" />
    <TicketInfoTableColumn
      col-key="reduce_shard_nodes"
      ellipsis
      :title="t('缩容至（节点数）')" />
  </TicketInfoTable>
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-title">{{ t('忽略业务连接') }}：</span>
      <span class="ticket-details-item-value">
        {{ ticketDetails.details.is_safe ? t('否') : t('是') }}
      </span>
    </div>
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mongodb.ReduceShardNodes>;
  }

  interface RowData {
    cluster_type: string;
    current_nodes: number;
    immute_domain: string;
    reduce_shard_nodes: number;
  }

  defineOptions({
    name: TicketTypes.MONGODB_REDUCE_SHARD_NODES,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = ref<RowData[]>([]);

  const { clusters, infos } = props.ticketDetails.details;

  tableData.value = infos.map((item) => {
    const cluster = clusters[item.cluster_ids[0]];
    return {
      cluster_type: cluster.cluster_type_name,
      current_nodes: item.current_shard_nodes_num,
      immute_domain: cluster.immute_domain,
      reduce_shard_nodes: item.current_shard_nodes_num - item.reduce_shard_nodes,
    };
  });
</script>
