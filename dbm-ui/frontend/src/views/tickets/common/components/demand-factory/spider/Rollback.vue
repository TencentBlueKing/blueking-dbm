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

  import type { SpiderRollbackDetails } from '@services/model/ticket/details/spider';
  import TicketModel from '@services/model/ticket/ticket';

  import { utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<SpiderRollbackDetails>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = computed(() => {
    const { details } = props.ticketDetails;
    const basicColumn = [
      {
        label: t('待构造集群'),
        field: 'clusterName',
        showOverflowTooltip: true,
      },
      {
        label: t('回档类型'),
        field: 'rollbackType',
        showOverflowTooltip: true,
      },
      {
        label: t('回档时间'),
        field: 'rollbackTime',
        showOverflowTooltip: true,
      },
      {
        label: t('构造 DB 名'),
        showOverflowTooltip: true,
        field: 'dbName',
      },
      {
        label: t('忽略DB名'),
        field: 'ignoreDbName',
        showOverflowTooltip: true,
      },
      {
        label: t('构造表名'),
        field: 'tableName',
        showOverflowTooltip: true,
      },
      {
        label: t('忽略表名'),
        field: 'ignoreTableName',
        showOverflowTooltip: true,
      },
    ];

    if (details.backupinfo.backup_id) {
      // 备份记录
      basicColumn.splice(2, 1, {
        label: t('备份时间'),
        field: 'backupTime',
        showOverflowTooltip: true,
      });
    }
    return basicColumn;
  });

  const tableData = computed(() => {
    const { details } = props.ticketDetails;
    return [
      {
        backupTime: utcDisplayTime(details.backupinfo.backup_time),
        clusterName: details.clusters[details.cluster_id].immute_domain,
        rollbackType: details.rollback_type === 'REMOTE_AND_BACKUPID' ? t('备份记录') : t('回档到指定时间'),
        rollbackTime: utcDisplayTime(details.rollback_time),
        dbName: details.databases.join(','),
        ignoreDbName: details.databases_ignore.join(','),
        tableName: details.tables.join(','),
        ignoreTableName: details.tables_ignore.join(','),
      },
    ];
  });
</script>
<style lang="less" scoped>
  @import '@views/tickets/common/styles/ticketDetails.less';
</style>
