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
  <BkLoading :loading="loading">
    <DbOriginalTable
      :columns="columns"
      :data="tableData" />
  </BkLoading>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { getList } from '@services/spider';
  import type { SpiderRollbackDetails, TicketDetails } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<SpiderRollbackDetails>
  }

  interface RowData {
    clusterName: string,
    rollbackType: string,
    rollbackTime: string,
    dbName: string,
    ignoreDbName: string,
    tableName: string,
    ignoreTableName: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  // eslint-disable-next-line vue/no-setup-props-destructure
  const { details } = props.ticketDetails;
  const tableData = ref<RowData[]>([]);
  const columns = [
    {
      label: t('待构造集群'),
      field: 'clusterName',
    },
    {
      label: t('回档类型'),
      field: 'rollbackType',
    },
    {
      label: t('回档时间'),
      field: 'rollbackTime',
    },
    {
      label: t('构造 DB 名'),
      field: 'dbName',
    },
    {
      label: t('忽略DB名'),
      field: 'ignoreDbName',
    },
    {
      label: t('构造表名'),
      field: 'tableName',
    },
    {
      label: t('忽略表名'),
      field: 'ignoreTableName',
    },
  ];

  const { loading } = useRequest(getList, {
    onSuccess: (r) => {
      if (r.results.length < 1) {
        return;
      }

      const clusterMap = r.results.reduce((obj, item) => {
        Object.assign(obj, { [item.id]: item.master_domain });
        return obj;
      }, {} as Record<number, string>);
      tableData.value = [
        {
          clusterName: clusterMap[details.cluster_id],
          rollbackType: details.rollbackup_type === 'REMOTE_AND_BACKUPID' ? t('备份记录') : t('回档到指定时间'),
          rollbackTime: details.rollback_time,
          dbName: details.databases.join(','),
          ignoreDbName: details.databases_ignore.join(','),
          tableName: details.tables.join(','),
          ignoreTableName: details.tables_ignore.join(','),
        },
      ];
    },
  });

</script>
<style lang="less" scoped>
  @import "@views/tickets/common/styles/ticketDetails.less";
</style>
