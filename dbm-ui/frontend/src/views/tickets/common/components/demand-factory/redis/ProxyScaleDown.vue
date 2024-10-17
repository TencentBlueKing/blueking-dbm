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

  import type { RedisProxyScaleDownDetails } from '@services/model/ticket/details/redis';
  import TicketModel from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<RedisProxyScaleDownDetails>
  }

  interface RowData {
    clusterName: string,
    clusterType: string,
    nodeType: string,
    hostSelectType: string,
    targetNum: number,
    switchMode: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { clusters, infos } = props.ticketDetails.details;
  const tableData = ref<RowData[]>([]);
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
      label: t('缩容节点类型'),
      field: 'nodeType',
    },
    {
      label: t('主机选择方式'),
      field: 'hostSelectType',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => (
        <div style="white-space: break-spaces; line-height: 18px">{data.hostSelectType}</div>
      )
    },
    {
      label: t('缩容数量（台）'),
      field: 'targetNum',
    },
    {
      label: t('切换模式'),
      field: 'switchMode',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.switchMode === 'user_confirm' ? t('需人工确认') : t('无需确认')}</span>,
    },
  ];

  tableData.value = infos.map((item) => {
    const ipList = (item.proxy_reduced_hosts || []).map(item => item.ip)
    return {
      clusterName: clusters[item.cluster_id].name,
      clusterType: clusters[item.cluster_id].cluster_type,
      clusterTypeName: clusters[item.cluster_id].cluster_type_name,
      nodeType: 'Proxy',
      hostSelectType: ipList.length > 0 ? ipList.join('\n') : t('自动匹配'),
      targetNum: item.proxy_reduce_count || ipList.length,
      switchMode: item.online_switch_type,
    };
  });
</script>
