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
    class="details-ha-truncate__table"
    :columns="columns"
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { MySQLHATruncateDetails, TicketDetails } from '@services/types/ticket';

  import { truncateDataTypes } from '@views/mysql/db-clear/common/const';

  interface Props {
    ticketDetails: TicketDetails<MySQLHATruncateDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  type truncateItem = {
    cluster_id: number,
    db_patterns: [],
    ignore_dbs: [],
    ignore_tables: [],
    table_patterns: []
    truncate_data_type: string,
    immute_domain: string,
    name: string,
  }

  /**
   *  替换主从清档
   */

  const columns: any = [{
    label: t('集群ID'),
    field: 'cluster_id',
    render: ({ cell }: { cell: number }) => <span>{cell || '--'}</span>,
  }, {
    label: t('集群名称'),
    field: 'immute_domain',
    showOverflowTooltip: false,
    render: ({ data }: { data: any }) => (
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
  }, {
    label: t('清档类型'),
    field: 'truncate_data_type',
    showOverflowTooltip: true,
    render: ({ cell }: { cell: string }) => (
      truncateDataTypes.filter(item => item.value === cell).map(item => <span>{item.label}</span>)
    ),
  }, {
    label: t('备份DB名'),
    field: 'db_patterns',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string[] }) => (
      <div class="text-overflow" v-overflow-tips={{
          content: cell,
        }}>
        {cell.map(item => <bk-tag>{item}</bk-tag>)}
      </div>
    ),
  }, {
    label: t('忽略DB名'),
    field: 'ignore_dbs',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string[] }) => (
      <div class="text-overflow" v-overflow-tips={{
          content: cell,
        }}>
        {cell.length > 0 ? cell.map(item => <bk-tag>{item}</bk-tag>) : '--'}
      </div>
    ),
  }, {
    label: t('备份表名'),
    field: 'table_patterns',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string[] }) => (
      <div class="text-overflow" v-overflow-tips={{
          content: cell,
        }}>
        {cell.map(item => <bk-tag>{item}</bk-tag>)}
      </div>
    ),
  }, {
    label: t('忽略表名'),
    field: 'ignore_tables',
    showOverflowTooltip: false,
    render: ({ cell }: { cell: string[] }) => (
      <div class="text-overflow" v-overflow-tips={{
          content: cell,
        }}>
        {cell.length > 0 ? cell.map(item => <bk-tag>{item}</bk-tag>) : '--'}
      </div>
    ),
  }];

  const dataList = computed(() => {
    const list: truncateItem[] = [];
    const infosData = props.ticketDetails?.details?.infos || [];
    const clusterIds = props.ticketDetails?.details?.clusters || {};
    infosData.forEach((item) => {
      const clusterData = clusterIds[item.cluster_id];
      list.push(Object.assign({
        cluster_id: item.cluster_id,
        db_patterns: item.db_patterns,
        ignore_dbs: item.ignore_dbs,
        ignore_tables: item.ignore_tables,
        table_patterns: item.table_patterns,
        truncate_data_type: item.truncate_data_type,
        immute_domain: clusterData.immute_domain,
        name: clusterData.name,
      }));
    });
    return list;
  });
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
