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
  import type { SpiderTruncateDatabaseDetails, TicketDetails } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<SpiderTruncateDatabaseDetails>
  }

  interface RowData {
    clusterName: string,
    type: string,
    dbName: string,
    ignoreDbName: string,
    tableName: string,
    ignoreTableName: string,
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  // eslint-disable-next-line vue/no-setup-props-destructure
  const { infos } = props.ticketDetails.details;
  const tableData = ref<RowData[]>([]);
  const columns = [
    {
      label: t('集群'),
      field: 'clusterName',
    },
    {
      label: t('清档类型'),
      minWidth: 200,
      field: 'type',
    },
    {
      label: t('指定DB名'),
      field: 'dbName',
    },
    {
      label: t('忽略DB名'),
      field: 'ignoreDbName',
    },
    {
      label: t('指定表名'),
      field: 'tableName',
    },
    {
      label: t('忽略表名'),
      field: 'ignoreTableName',
    },
  ];

  const typesMap = {
    truncate_table: t('清除表数据_truncatetable'),
    drop_table: t('清除表数据和结构_droptable'),
    drop_database: t('删除整库_dropdatabase'),
  };

  const { loading } = useRequest(getList, {
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
          type: typesMap[item.truncate_data_type],
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
<style lang="less" scoped>
  @import "@views/tickets/common/styles/ticketDetails.less";
</style>
