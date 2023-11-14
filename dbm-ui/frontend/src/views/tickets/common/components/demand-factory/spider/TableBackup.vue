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

  import { getSpiderList } from '@services/source/spider';
  import type { SpiderTableBackupDetails, TicketDetails } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<SpiderTableBackupDetails>
  }

  interface RowData {
    clusterName: string,
    position: string,
    dbName: string,
    tableName: string,
    ignoreDbName: string,
    ignoreTableName: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  // eslint-disable-next-line vue/no-setup-props-destructure
  const { infos } = props.ticketDetails.details;
  const tableData = ref<RowData[]>([]);
  const columns = [
    {
      label: t('目标集群'),
      field: 'clusterName',
      showOverflowTooltip: true,
    },
    {
      label: t('备份位置'),
      field: 'position',
      showOverflowTooltip: true,
    },
    {
      label: t('备份DB名'),
      field: 'dbName',
      showOverflowTooltip: true,
    },
    {
      label: t('备份表名'),
      field: 'tableName',
      showOverflowTooltip: true,
    },
    {
      label: t('忽略DB名'),
      field: 'ignoreDbName',
      showOverflowTooltip: true,
    },
    {
      label: t('忽略表名'),
      field: 'ignoreTableName',
      showOverflowTooltip: true,
    },
  ];

  const { loading } = useRequest(getSpiderList, {
    onSuccess: (r) => {
      if (r.results.length < 1) {
        return;
      }
      const clusterMap = r.results.reduce((obj, item) => {
        Object.assign(obj, { [item.id]: item.master_domain });
        return obj;
      }, {} as Record<number, string>);

      tableData.value = infos.reduce((results, item) => {
        const obj = {
          clusterName: clusterMap[item.cluster_id],
          position: item.backup_local,
          dbName: item.db_patterns.join(','),
          tableName: item.table_patterns.join(','),
          ignoreDbName: item.ignore_dbs.join(','),
          ignoreTableName: item.ignore_tables.join(','),
        };
        results.push(obj);
        return results;
      }, [] as RowData[]);
    },
  });

</script>
