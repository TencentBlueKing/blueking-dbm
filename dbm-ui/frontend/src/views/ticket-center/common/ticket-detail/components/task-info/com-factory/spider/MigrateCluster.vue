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
    class="details-migrate__table"
    :columns="columns"
    :data="dataList" />
  <DemandInfo
    :config="config"
    :data="ticketDetails" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { SpiderMigrateCluster } from '@services/model/ticket/details/spider';
  import TicketModel from '@services/model/ticket/ticket';

  import DemandInfo, {
    type DemandInfoConfig,
  } from '../components/DemandInfo.vue';

  interface Props {
    ticketDetails: TicketModel<SpiderMigrateCluster>
  }

  type dataItem = {
    clusterId: number,
    newMasterIp: string,
    newSlaveIp: string,
    domain: string,
    name: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const config: DemandInfoConfig[] = [
    {
      list: [
        {
          label: t('备份源'),
          key: 'details.backup_source',
          render: () => props.ticketDetails.details.backup_source === 'local' ? t('本地备份') : t('远程备份')
        },
      ],
    },
  ]

  const columns = [
    {
      label: t('集群ID'),
      field: 'clusterId',
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('集群名称'),
      field: 'immute_domain',
      showOverflowTooltip: false,
      render: ({ data }: { data: dataItem }) => (
        <div class="cluster-name text-overflow"
          v-overflow-tips={{
            content: `
              <p>${t('域名')}：${data.domain}</p>
              ${data.name ? `<p>${('集群别名')}：${data.name}</p>` : null}
            `,
            allowHTML: true,
        }}>
          <span>{data.domain}</span><br />
          <span class="cluster-name__alias">{data.name}</span>
        </div>
      ),
    },
    {
      label: t('新主库IP'),
      field: 'newMasterIp',
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('新从库IP'),
      field: 'newSlaveIp',
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    }
  ];

  const dataList = computed(() => {
    const { infos, clusters } = props.ticketDetails.details;
    const result: dataItem[] = []
    infos.forEach(infoItem => {
      const clusterData = clusters[infoItem.cluster_id];
      result.push({
        clusterId: infoItem.cluster_id,
        newMasterIp: infoItem.new_master.ip,
        newSlaveIp: infoItem.new_slave.ip,
        domain: clusterData.immute_domain,
        name: clusterData.name,
      })
    })
    return result;
  });
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
