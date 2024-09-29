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
    ticketDetails: TicketModel<TendbCluster.RestoreSlave>
  }

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_RESTORE_SLAVE,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  type dataItem = {
    cluster_id: number,
    new_slave: string;
    immute_domain: string,
    backup_source: string
  }


  const columns = [
    {
      label: t('集群ID'),
      field: 'cluster_id',
      render: ({ data }: { data: dataItem }) => <span>{data.cluster_id || '--'}</span>,
    },
    {
      label: t('集群名称'),
      field: 'immute_domain',
    },
    {
      label: t('新从库主机'),
      field: 'new_slave',
      render: ({ data }: { data: dataItem }) => <span>{data.new_slave || '--'}</span>,
    },
    {
      label: t('备份源'),
      field: 'backup_source',
      render: ({ data }: { data: dataItem }) => <span>{data.backup_source === 'local' ? t('本地备份') : '--'}</span>,
    }
  ];

  const dataList = computed(() => {
    const infosList = props.ticketDetails.details.infos;
    const clusterMap = props.ticketDetails.details.clusters;
    const backupSource = props.ticketDetails.details.backup_source
    return infosList.reduce((prevInfoList, infoItem) => {
      const clusterItem = clusterMap[infoItem.cluster_id]
      const oldSlave = infoItem.old_slave
      return [...prevInfoList, {
        cluster_id: infoItem.cluster_id,
        new_slave: oldSlave.ip,
        immute_domain: clusterItem.immute_domain,
        name: clusterItem.name,
        backup_source: backupSource
      }]
    }, [] as dataItem[]);
  });
</script>
