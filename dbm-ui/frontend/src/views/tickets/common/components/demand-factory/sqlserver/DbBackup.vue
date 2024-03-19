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
  <DemandInfo
  :config="config"
  :data="ticketDetails" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { TicketDetails } from '@services/types/ticket';

  import type { SqlserverDbBackup } from '../common/types';
  import DemandInfo, {
    type DemandInfoConfig,
  } from '../components/DemandInfo.vue';

  type backupItem = {
    cluster_id: number,
    backup_dbs: string[],
    immute_domain: string,
    name: string,
  }

  interface Props {
    ticketDetails: TicketDetails<SqlserverDbBackup>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const {
    backup_type: backupType,
    backup_place: backupPlace,
    file_tag: fileTag,
    infos,
    clusters
  } = props.ticketDetails.details

  const infosData = infos || [];
  const clusterIds = clusters || {};
  const dataList = infosData.reduce((prev, infoItem) => {
    const clusterData = clusterIds[infoItem.cluster_id];
    return [...prev, {
      cluster_id: infoItem.cluster_id,
      backup_dbs: infoItem.backup_dbs,
      immute_domain: clusterData.immute_domain,
      name: clusterData.name,
    }]
  }, [] as backupItem[]);

  const backupPlaceMap: Record<string, string> = {
    master: t('主库主机')
  }

  const config: DemandInfoConfig[] = [
    {
      title: '',
      list: [
        {
          label: t('备份方式'),
          render: () => backupType === 'full_backup' ? t('全量备份') : t('增量备份'),
        },
        {
          label: t('备份位置'),
          render: () => backupPlaceMap[backupPlace]
        },
        {
          label: t('备份保存时间'),
          render: () => {
            if (backupType === 'full_backup') {
              return fileTag === 'LONGDAY_DBFILE_3Y' ? `3 ${t('年')}` : `30 ${t('天')}`
            }
            return `15 ${t('天')}`
          }
        },
        {
          label: t('集群详情'),
          isTable: true,
          render: () => (
            <db-original-table
              class="details-table-backup__table"
              columns={columns}
              data={dataList} />
          )
        },
      ],
    },
  ]

  const columns = [
    {
      label: t('集群ID'),
      field: 'cluster_id',
      render: ({ cell }: { cell: number }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('集群名称'),
      field: 'immute_domain',
      showOverflowTooltip: false,
      render: ({ data }: { data: backupItem }) => (
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
      label: t('备份DB名'),
      field: 'backup_dbs',
      showOverflowTooltip: false,
      render: ({ cell }: { cell: string[] }) => (
        <div class="text-overflow" v-overflow-tips={{
            content: cell,
          }}>
          {cell.map(item => <bk-tag class="mr-4">{item}</bk-tag>)}
        </div>
      ),
    }
  ];
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
