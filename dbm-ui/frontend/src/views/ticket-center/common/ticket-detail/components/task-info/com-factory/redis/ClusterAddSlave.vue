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

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.ClusterAddSlave>
  }

  interface RowData {
    hostIp: string,
    clusterName: string,
    clusterType: string,
    sepc: {
      id: number,
      name: string,
    },
    targetNum: number,
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_ADD_SLAVE,
    inheritAttrs: false
  })

  const { t } = useI18n();

  const tableData = ref<RowData[]>([]);

  const { infos, clusters, specs } = props.ticketDetails.details;

  const columns = [
    {
      label: t('待重建从库主机'),
      field: 'slaveIp',
      showOverflowTooltip: true,
    },
    {
      label: t('目标主库主机'),
      field: 'hostIp',
      showOverflowTooltip: true,
    },
    {
      label: t('所属集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('规格需求'),
      field: 'sepc',
      showOverflowTooltip: true,
      render: ({ data }: {data: RowData}) => <span>{data.sepc.name}</span>,
    },
    {
      label: t('新增从库主机数量'),
      field: 'targetNum',
    },
  ];

  tableData.value = infos.reduce((results, item) => {
    item.pairs.forEach((pair) => {
      const specInfo = specs[pair.redis_slave.spec_id];
      const obj = {
        slaveIp: pair.redis_slave.old_slave_ip,
        hostIp: pair.redis_master.ip,
        clusterName: item.cluster_id
          ? clusters[item.cluster_id].immute_domain // 兼容旧单据
          : item.cluster_ids.map(id => clusters[id].immute_domain).join(','),
        clusterType: clusters[item.cluster_ids[0]].cluster_type,
        sepc: {
          id: pair.redis_slave.spec_id,
          name: specInfo ? specInfo.name : '',
        },
        targetNum: pair.redis_slave.count,
      };
      results.push(obj);
    });
    return results;
  }, [] as RowData[]);
</script>
