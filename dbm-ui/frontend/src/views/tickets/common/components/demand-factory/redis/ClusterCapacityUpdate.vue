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
  import type { RedisScaleUpDownDetails } from '@services/model/ticket/details/redis';
  import TicketModel from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<RedisScaleUpDownDetails>
  }

  interface RowData {
    clusterName: string,
    clusterType: string,
    sepc: {
      id: number,
      name: string,
    },
    shardNum: number,
    groupNum: number,
    capacity: number,
    futureCapacity: number,
    dbVersion: string,
    switchMode: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = ref<RowData[]>([]);

  const { clusters, infos, specs } = props.ticketDetails.details;

  const columns = [
    {
      label: t('目标集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('架构版本'),
      field: 'clusterTypeName',
      showOverflowTooltip: true,
    },
    {
      label: t('集群分片数'),
      field: 'shardNum',
      showOverflowTooltip: true,
    },
    {
      label: t('部署机器组数'),
      field: 'groupNum',
      showOverflowTooltip: true,
    },
    {
      label: t('当前容量需求'),
      field: 'capacity',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.capacity}G</span>,
    },
    {
      label: t('未来容量需求'),
      field: 'futureCapacity',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.futureCapacity}G</span>,
    },
    {
      label: t('目标资源规格'),
      field: 'sepc',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.sepc.name}</span>,
    },
    {
      label: t('指定Redis版本'),
      field: 'dbVersion',
      showOverflowTooltip: true,
    },
    {
      label: t('切换模式'),
      field: 'switchMode',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.switchMode === 'user_confirm' ? t('需人工确认') : t('无需确认')}</span>,
    },
  ];

  tableData.value = infos.map((item) => {
    return {
      clusterName: clusters[item.cluster_id].immute_domain,
      clusterType: clusters[item.cluster_id].cluster_type,
      clusterTypeName: clusters[item.cluster_id].cluster_type_name,
      shardNum: item.shard_num,
      groupNum: item.group_num,
      dbVersion: item.db_version,
      capacity: item.capacity,
      futureCapacity: item.future_capacity,
      sepc: {
        id: item.resource_spec.backend_group.spec_id,
        name: specs[item.resource_spec.backend_group.spec_id].name,
      },
      switchMode: item.online_switch_type,
    };
  });
</script>
