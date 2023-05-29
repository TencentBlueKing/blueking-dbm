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

  import type { RedisDBReplaceDetails } from '@services/model/ticket/details/redis';
  import TicketModel from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<RedisDBReplaceDetails>
  }

  interface RowData {
    ip: string,
    role: string,
    clusterName: string,
    clusterType: string,
    sepc: {
      id: number,
      name: string,
    },
  }

  const props = defineProps<Props>();

  const { t } = useI18n();



  const columns = [
    {
      label: t('待替换的主机'),
      field: 'ip',
      showOverflowTooltip: true,
    },
    {
      label: t('角色类型'),
      field: 'role',
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
  ];

  const tableData = computed(() => {
    const {
      clusters,
      infos,
      specs,
    } = props.ticketDetails.details;

    return infos.reduce((results, item) => {
      if (item.proxy.length > 0) {
        item.proxy.forEach((proxyItem) => {
          const specInfo = specs[proxyItem.spec_id];
          const obj = {
            ip: proxyItem.ip,
            role: 'Proxy',
            clusterName: clusters[item.cluster_id].immute_domain,
            clusterType: clusters[item.cluster_id].cluster_type,
            sepc: {
              id: proxyItem.spec_id,
              name: specInfo ? specInfo.name : '',
            },
          };
          results.push(obj);
        });
      }
      if (item.redis_master.length > 0) {
        item.redis_master.forEach((masterItem) => {
          const specInfo = specs[masterItem.spec_id];
          const obj = {
            ip: masterItem.ip,
            role: 'Master',
            clusterName: clusters[item.cluster_id].immute_domain,
            clusterType: clusters[item.cluster_id].cluster_type,
            sepc: {
              id: masterItem.spec_id,
              name: specInfo ? specInfo.name : '',
            },
          };
          results.push(obj);
        });
      }
      if (item.redis_slave.length > 0) {
        item.redis_slave.forEach((slaveItem) => {
          const specInfo = specs[slaveItem.spec_id];
          const obj = {
            ip: slaveItem.ip,
            role: 'Slave',
            clusterName: clusters[item.cluster_id].immute_domain,
            clusterType: clusters[item.cluster_id].cluster_type,
            sepc: {
              id: slaveItem.spec_id,
              name: specInfo ? specInfo.name : '',
            },
          };
          results.push(obj);
        });
      }

      return results;
    }, [] as RowData[])
  });
</script>
