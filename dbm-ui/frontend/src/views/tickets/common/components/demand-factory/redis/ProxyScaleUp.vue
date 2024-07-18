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
  import type { RedisProxyScaleUpDetails } from '@services/model/ticket/details/redis';
  import TicketModel from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<RedisProxyScaleUpDetails>
  }

  interface RowData {
    clusterName: string,
    clusterType: string,
    nodeType: string,
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
      label: t('扩容节点类型'),
      field: 'nodeType',
    },
    {
      label: t('当前规格'),
      field: 'sepc',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.sepc.name}</span>,
    },
    {
      label: t('扩容至(台)'),
      field: 'targetNum',
    },
  ];

  const tableData = infos.map((item) => {
    return {
      clusterName: clusters[item.cluster_id].immute_domain,
      clusterType: clusters[item.cluster_id].cluster_type,
      clusterTypeName: clusters[item.cluster_id].cluster_type_name,
      nodeType: 'Proxy',
      sepc: {
        id: item.resource_spec.proxy.spec_id,
        name: specs[item.resource_spec.proxy.spec_id].name,
      },
      targetNum: item.target_proxy_count,
    };
  });
</script>
