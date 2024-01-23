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
    class="details-cluster__table"
    :columns="columns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { TicketDetails } from '@services/types/ticket';

  type Infos = {
    cluster_id: number,
    shard_machine_group: number,
    shard_node_count: number,
  }

  interface Props {
    ticketDetails: TicketDetails<{
      ip_source: string,
      infos: Infos[]
    }>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      label: t('集群ID'),
      field: 'cluster_id',
      render: ({ data }: { data: Infos }) => <span>{data.cluster_id || '--'}</span>,
    },
    {
      label: t('所需机组数'),
      field: 'shard_machine_group',
      render: ({ data }: { data: Infos }) => <span>{data.shard_machine_group || '--'}</span>,
    },
    {
      label: t('每个Shard节点数'),
      field: 'shard_node_count',
      render: ({ data }: { data: Infos }) => <span>{data.shard_node_count || '--'}</span>,
    },
  ];

  const dataList = computed(() => props.ticketDetails?.details?.infos || []);
</script>

<style lang="less" scoped>
@import "@views/tickets/common/styles/DetailsTable.less";
</style>
