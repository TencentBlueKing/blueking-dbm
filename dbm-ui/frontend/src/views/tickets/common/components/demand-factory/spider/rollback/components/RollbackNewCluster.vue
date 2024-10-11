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
    class="details-rollback__table"
    :columns="columns"
    :data="tableData" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { SpiderRollbackDetails } from '@services/model/ticket/details/spider';
  import TicketModel from '@services/model/ticket/ticket';

  import { backupSourceList, type BackupSources } from '@views/db-manage/mysql/rollback/pages/page1/components/render-row/components/RenderBackup.vue';

  import { utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<SpiderRollbackDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      label: t('集群名称'),
      field: 'cluster_name',
      width: 220,
      render: ({ cell }: { cell: string }) => <span>{ cell || '--' }</span>,
    },
    {
      label: t('主机来源'),
      field: '',
      width: 100,
      render: () => <span>{t('业务空闲机')}</span>,
    },
    {
      label: t('存储层主机'),
      field: 'remote_hosts',
      width: 120,
      render: ({ data }: { data: SpiderRollbackDetails['infos'][0] }) => <span>{data.rollback_host.remote_hosts?.map(item => item.ip) || '--'}</span>,
    },
    {
      label: t('接入层主机'),
      field: 'spider_host',
      width: 120,
      render: ({ data }: { data: SpiderRollbackDetails['infos'][0] }) => <span>{data.rollback_host.spider_host?.ip || '--'}</span>,
    },
    {
      label: t('备份源'),
      field: 'backup_source',
      width: 100,
      render: ({ cell }: { cell: BackupSources }) => <span>{ backupSourceList.find(item=>item.value === cell)?.label || '--' }</span>,
    },
    {
      label: t('回档类型'),
      field: '',
      width: 280,
      render: ({ data }: { data: SpiderRollbackDetails['infos'][0] }) =>  {
        if (data.rollback_time) {
          return <span>{ t('回档到指定时间') } - { utcDisplayTime(data.rollback_time) }</span>;
        }
        if (data.backupinfo?.backup_time) {
          return <span>{ t('备份记录') } - { utcDisplayTime(data.backupinfo?.backup_time) }</span>;
        }
        return '--';
      },
    },
    {
      label: t('回档DB名'),
      field: 'databases',
      showOverflowTooltip: false,
      render: ({ cell }: { cell: string[] }) => (
        <div
          class="text-overflow"
          v-overflow-tips={{
            content: cell,
          }}>
            { cell.map(item => <bk-tag>{ item }</bk-tag>) }
        </div>
      ),
    },
    {
      label: t('忽略DB名'),
      field: 'databases_ignore',
      showOverflowTooltip: false,
      render: ({ cell }: { cell: string[] }) => (
        <div
          class="text-overflow"
          v-overflow-tips={{
            content: cell,
          }}>
            { cell.length > 0 ? cell.map(item => <bk-tag>{ item }</bk-tag>) : '--' }
        </div>
      ),
    },
    {
      label: t('回档表名'),
      field: 'tables',
      showOverflowTooltip: false,
      render: ({ cell }: { cell: string[] }) => (
        <div
          class="text-overflow"
          v-overflow-tips={{
            content: cell,
          }}>
            { cell.map(item => <bk-tag>{ item }</bk-tag>) }
        </div>
      ),
    },
    {
      label: t('忽略表名'),
      field: 'tables_ignore',
      showOverflowTooltip: false,
      render: ({ cell }: { cell: string[] }) => (
        <div
          class="text-overflow"
          v-overflow-tips={{
            content: cell,
          }}>
            { cell.length > 0 ? cell.map(item => <bk-tag>{ item }</bk-tag>) : '--' }
        </div>
      ),
    },
  ];

  const tableData = computed(()=>{
    const { clusters, infos } = props.ticketDetails.details;
    return (infos || []).map(item => ({
      ...item,
      cluster_name: clusters[item.cluster_id].immute_domain,
      backup_source: item.rollback_type?.split('_AND_')[0].toLocaleLowerCase()
    }));
  })
</script>
