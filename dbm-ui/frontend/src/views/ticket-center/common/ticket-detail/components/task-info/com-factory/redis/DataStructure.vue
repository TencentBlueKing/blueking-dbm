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

  import type { RedisDataStructrueDetails } from '@services/model/ticket/details/redis';
  import TicketModel from '@services/model/ticket/ticket';

  import { utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<RedisDataStructrueDetails>
  }

  interface RowData {
    clusterName: string,
    clusterType: string,
    clusterTypeName: string;
    instances: string[],
    time: string,
    sepc: {
      id: number,
      name: string,
    },
    targetNum: number,
  }


  const props = defineProps<Props>();

  const { t } = useI18n();

  const { clusters, infos, specs } = props.ticketDetails.details;

  const columns = [
    {
      label: t('待构造的集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('架构版本'),
      field: 'clusterTypeName',
      showOverflowTooltip: true,
    },
    {
      label: t('待构造的实例'),
      field: 'instances',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.instances.join(',')}</span>,
    },
    {
      label: t('规格需求'),
      field: 'sepc',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.sepc.name}</span>,
    },
    {
      label: t('构造主机数量'),
      field: 'targetNum',
    },
    {
      label: t('构造到指定时间'),
      field: 'time',
      showOverflowTooltip: true,
    },
  ];

  const tableData = infos.map((item) => ({
    clusterName: clusters[item.cluster_id].immute_domain,
    clusterType: clusters[item.cluster_id].cluster_type,
    clusterTypeName: clusters[item.cluster_id].cluster_type_name,
    instances: item.master_instances,
    time: utcDisplayTime(item.recovery_time_point),
    sepc: {
      id: item.resource_spec.redis.spec_id,
      name: specs[item.resource_spec.redis.spec_id].name,
    },
    targetNum: item.resource_spec.redis.count,
  }));
</script>
