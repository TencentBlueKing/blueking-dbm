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
  <DbOriginalTable
    :columns="columns"
    :data="tableData" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mongodb.ReduceMongos>;
  }

  interface RowData {
    immute_domain: string;
    node_type: string;
    reduce_ips: string;
    reduce_shard_num: number;
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.MONGODB_REDUCE_MONGOS,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const tableData = ref<RowData[]>([]);

  const { clusters, infos } = props.ticketDetails.details;

  const columns = [
    {
      label: t('目标分片集群'),
      field: 'immute_domain',
      showOverflowTooltip: true,
    },
    {
      label: t('缩容节点类型'),
      field: 'node_type',
    },
    {
      label: t('缩容的IP'),
      field: 'reduce_ips',
      showOverflowTooltip: true,
    },
    {
      label: t('缩容数量（台）'),
      field: 'reduce_shard_num',
    },
  ];

  tableData.value = infos.map((item) => ({
    immute_domain: clusters[item.cluster_id].immute_domain,
    node_type: 'mongos',
    reduce_ips: item.reduce_nodes.map((item) => item.ip).join(' , '),
    reduce_shard_num: item.reduce_nodes.length,
  }));
</script>
