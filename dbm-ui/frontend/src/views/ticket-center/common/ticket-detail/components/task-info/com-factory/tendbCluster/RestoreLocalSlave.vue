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
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.RestoreLocalSlave>
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  type RowData = Props['ticketDetails']['details']['infos'][number];

  type dataItem = {
    cluster_id: number,
    slave: string,
    immute_domain: string,
    backup_source: string
  }

  // 原地重建
  const columns = [
    {
      label: t('集群ID'),
      field: 'cluster_id',
      render: ({ data }: { data: dataItem }) => <span>{data.cluster_id || '--'}</span>,
    },
    {
      label: t('集群名称'),
      field: 'immute_domain',
      showOverflowTooltip: false,
    },
    {
      label: t('目标从库实例'),
      field: 'slave',
      render: ({ data }: { data: dataItem }) => `${data.slave.ip}:${data.slave.port}`,
    },
    {
      label: t('所属集群'),
      field: 'backup_source',
      render: ({ data }: { data: RowData }) => props.ticketDetails.details.clusters[data.cluster_id].immute_domain,
    },
  ];


  const dataList = computed(() => {
    const infosList = props.ticketDetails.details.infos;
    const clusterMap = props.ticketDetails.details.clusters;
    const backupSource = props.ticketDetails.details.backup_source
    return infosList.reduce((prevInfoList, infoItem) => {
      const clusterItem = clusterMap[infoItem.cluster_id]
      const oldSlave = infoItem.slave
      return [...prevInfoList, {
        cluster_id: infoItem.cluster_id,
        slave: `${oldSlave.ip}:${oldSlave.port}`,
        immute_domain: clusterItem.immute_domain,
        name: clusterItem.name,
        backup_source: backupSource
      }]
    }, [] as dataItem[]);
  });
</script>
