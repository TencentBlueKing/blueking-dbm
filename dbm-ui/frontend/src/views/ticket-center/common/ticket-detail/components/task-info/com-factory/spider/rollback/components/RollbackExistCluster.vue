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

  import type TendbclusterModel from '@services/model/tendbcluster/tendbcluster';
  import type { MySQLRollbackDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';
  import { getTendbclusterListByBizId } from '@services/source/tendbcluster';

  import { type BackupSources, selectList } from '@views/db-manage/mysql/rollback/pages/page1/components/common/const';

  import { utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<MySQLRollbackDetails>
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
      label: t('目标集群'),
      field: 'target_cluster_name',
      width: 220,
      render: ({ cell }: { cell: string }) => <span>{ cell || '--' }</span>,
    },
    {
      label: t('备份源'),
      field: 'backup_source',
      width: 100,
      render: ({ cell }: { cell: BackupSources }) => <span>{ selectList.backupSource.find(item=>item.value === cell)?.label || '--' }</span>,
    },
    {
      label: t('回档类型'),
      field: '',
      width: 280,
      render: ({ data }: { data: MySQLRollbackDetails['infos'][0] }) =>  {
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

  const targetClusters = shallowRef<Array<TendbclusterModel>>([]);

  const tableData = computed(()=>{
    const { clusters, infos } = props.ticketDetails.details;
    return (infos || []).map(item => ({
      ...item,
      cluster_name: clusters[item.cluster_id].immute_domain,
      target_cluster_name: targetClusters.value.map(item=>item.master_domain).join(','),
      backup_source: item.rollback_type?.split('_AND_')[0].toLocaleLowerCase()
    }));
  })

  watch(
    ()=> props.ticketDetails.details,
    () => {
      const targetClusterIds = props.ticketDetails.details.infos.map(item => Number(item.target_cluster_id));
      getTendbclusterListByBizId({
        cluster_ids: targetClusterIds,
        bk_biz_id: props.ticketDetails.bk_biz_id,
      }).then((data) => {
        targetClusters.value = data.results;
      })
    },
    {
      immediate: true
    }
  )
</script>
