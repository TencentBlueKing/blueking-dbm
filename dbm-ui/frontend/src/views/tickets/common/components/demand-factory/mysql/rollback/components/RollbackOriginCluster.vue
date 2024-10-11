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

  import type { MySQLRollbackDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';

  import { backupSourceList, type BackupSources } from '@views/db-manage/mysql/rollback/pages/page1/components/render-row/components/RenderBackup.vue';

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
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('备份源'),
      field: 'backup_source',
      render: ({ cell }: { cell: BackupSources }) => <span>{ backupSourceList.find(item => item.value === cell)?.label || '--' }</span>,
    },
    {
      label: t('回档类型'),
      field: '',
      render: ({ data }: { data: MySQLRollbackDetails['infos'][0] }) => {
        if (data.rollback_time) {
          return <span>{ t('回档到指定时间') } - { utcDisplayTime(data.rollback_time) }</span>;
        }
        if (data.backupinfo?.backup_time && data.backupinfo?.mysql_role) {
          return <span>{ t('备份记录') } - { data.backupinfo?.mysql_role } { utcDisplayTime(data.backupinfo?.backup_time) }</span>;
        }
        return '--';
      },
    },
  ];

  const tableData = computed(()=>{
    const { clusters, infos } = props.ticketDetails.details;
    return infos.map(item => ({
      ...item,
      cluster_name: clusters[item.cluster_id].immute_domain,
    }));
  })
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
