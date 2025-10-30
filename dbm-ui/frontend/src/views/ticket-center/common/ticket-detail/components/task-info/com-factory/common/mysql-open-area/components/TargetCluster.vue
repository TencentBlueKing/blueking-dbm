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
  <TicketInfoTable
    class="target-cluster-table"
    :data="tableData"
    row-key="targetCluster"
    :rowspan-and-colspan="rowspanAndColspan">
    <TicketInfoTableColumn
      col-key="targetCluster"
      :get-copy-value="(row: RowData) => row.targetCluster"
      :min-width="200"
      :title="t('目标集群')"
      :width="250" />
    <TicketInfoTableColumn
      col-key="newDb"
      :min-width="150"
      :title="t('新DB')"
      :width="200" />
    <TicketInfoTableColumn
      col-key="ips"
      ellipsis
      :get-copy-value="(row: RowData) => row.ips.split(',')"
      :title="t('授权的IP')">
      <template #default="{ row }: { row: RowData }">
        {{ row.ips || '--' }}
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import type { BaseTableCellParams, TableRowData } from 'tdesign-vue-next/es/table/type';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<Mysql.OpenArea>;
  }

  interface RowData {
    ips: string;
    newDb: string;
    targetCluster: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const clustersMap = props.ticketDetails.details.clusters;
  const clusterIpsMap = props.ticketDetails.details.rules_set.reduce<Record<string, string[]>>(
    (acc, { source_ips, target_instances: [cluster] }) => {
      return Object.assign(acc, {
        [cluster]: _.uniq((acc[cluster] || []).concat(source_ips)),
      });
    },
    {},
  );

  const tableData = computed(() =>
    _.flatMap(
      _.sortBy(
        props.ticketDetails.details.config_data.map((item) => {
          const cluster = clustersMap[item.cluster_id]?.immute_domain;
          return item.execute_objects.map((executeObject) => ({
            ips: clusterIpsMap[cluster]?.join(',') || '',
            newDb: executeObject.target_db,
            targetCluster: cluster,
          }));
        }),
        'newDb',
      ),
    ),
  );

  const rowspanAndColspan = (params: BaseTableCellParams<TableRowData>) => {
    const { col, row } = params;
    if (col.colKey === 'targetCluster') {
      const rowSpan = tableData.value.filter((item: RowData) => item.targetCluster === row.targetCluster).length;
      return { colspan: 1, rowspan: rowSpan > 1 ? rowSpan : 1 };
    }
    return {};
  };
</script>

<style lang="less" scoped>
  .target-cluster-table {
    :deep(.cell) {
      .copy-btn {
        display: none;
        margin-left: 4px;
        color: @primary-color;
        cursor: pointer;
      }
    }

    :deep(tr:hover) {
      .copy-btn[is-show='true'] {
        display: inline-block !important;
      }
    }
  }
</style>
