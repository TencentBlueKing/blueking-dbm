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
    class="details-slave__table"
    :columns="renderColumns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { SpiderSlaveRebuid } from '@services/model/ticket/details/spider';
  import TicketModel from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<SpiderSlaveRebuid>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  type dataItem = {
    cluster_id: number,
    slave: string,
    new_slave: string;
    immute_domain: string,
    name: string,
    backup_source: string
  }

  // 原地重建
  const localSlaveColumns = [
    {
      label: t('集群ID'),
      field: 'cluster_id',
      render: ({ data }: { data: dataItem }) => <span>{data.cluster_id || '--'}</span>,
    },
    {
      label: t('集群名称'),
      field: 'immute_domain',
      showOverflowTooltip: false,
      render: ({ data }: { data: dataItem }) => (
        <div class="cluster-name text-overflow"
          v-overflow-tips={{
            content: `
              <p>${t('域名')}：${data.immute_domain}</p>
              ${data.name ? `<p>${('集群别名')}：${data.name}</p>` : null}
            `,
            allowHTML: true,
        }}>
          <span>{data.immute_domain}</span><br />
          <span class="cluster-name__alias">{data.name}</span>
        </div>
      ),
    },
    {
      label: t('目标从库实例'),
      field: 'slave',
      render: ({ data }: { data: dataItem }) => <span>{data.slave || '--'}</span>,
    },
    {
      label: t('备份源'),
      field: 'backup_source',
      render: ({ data }: { data: dataItem }) => <span>{data.backup_source === 'local' ? t('本地备份') : '--'}</span>,
    }
  ];


  const addSlaveColumns = [
    {
      label: t('集群ID'),
      field: 'cluster_id',
      render: ({ data }: { data: dataItem }) => <span>{data.cluster_id || '--'}</span>,
    },
    {
      label: t('集群名称'),
      field: 'immute_domain',
      showOverflowTooltip: false,
      render: ({ data }: { data: dataItem }) => (
        <div class="cluster-name text-overflow"
          v-overflow-tips={{
            content: `
              <p>${t('域名')}：${data.immute_domain}</p>
              ${data.name ? `<p>${('集群别名')}：${data.name}</p>` : null}
            `,
            allowHTML: true,
        }}>
          <span>{data.immute_domain}</span><br />
          <span class="cluster-name__alias">{data.name}</span>
        </div>
      ),
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

  const renderColumns = props.ticketDetails.ticket_type === TicketTypes.TENDBCLUSTER_RESTORE_LOCAL_SLAVE ? localSlaveColumns : addSlaveColumns;

  const dataList = computed(() => {
    const infosList = props.ticketDetails.details.infos;
    const clusterMap = props.ticketDetails.details.clusters;
    const backupSource = props.ticketDetails.details.backup_source
    return infosList.reduce((prevInfoList, infoItem) => {
      const clusterItem = clusterMap[infoItem.cluster_id]
      const oldSlave = infoItem.slave || infoItem.old_slave
      return [...prevInfoList, {
        cluster_id: infoItem.cluster_id,
        slave: oldSlave.ip,
        new_slave: infoItem.new_slave?.ip || '',
        immute_domain: clusterItem.immute_domain,
        name: clusterItem.name,
        backup_source: backupSource
      }]
    }, [] as dataItem[]);
  });
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
