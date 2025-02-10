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
    class="target-cluster-table"
    :columns="columns"
    :data="tableData" />
</template>

<script setup lang="tsx">
  import _ from 'lodash';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { execCopy } from '@utils';

  interface Props {
    ticketDetails: TicketModel<Mysql.OpenArea>;
  }

  interface RowData {
    targetCluster: string;
    newDb: string;
    ips: string;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const clustersMap = props.ticketDetails.details.clusters;
  const clusterIpsMap = props.ticketDetails.details.rules_set.reduce<Record<string, string[]>>((acc, { target_instances: [cluster], source_ips }) => {
    acc[cluster] = _.uniq((acc[cluster] || []).concat(source_ips));
    return acc;
  }, {});

  const tableData = computed(() =>
    _.flatMap(
      _.sortBy(
      props.ticketDetails.details.config_data.map((item) => {
        const cluster = clustersMap[item.cluster_id]?.immute_domain;
        return item.execute_objects.map((executeObject) => ({
          targetCluster: cluster,
          newDb: executeObject.target_db,
          ips: clusterIpsMap[cluster]?.join(',') || '',
        }));
      }), 'newDb')
    ),
  );

  const columns = computed(() => [
    {
      label: t('目标集群'),
      field: 'targetCluster',
      minWidth: 200,
      width: 250,
      rowspan: ({ row }: { row: RowData }) => {
        const { targetCluster } = row;
        const rowSpan = tableData.value.filter((item) => item.targetCluster === targetCluster).length;
        return rowSpan > 1 ? rowSpan : 1;
      },
    },
    {
      label: t('新DB'),
      field: 'newDb',
      minWidth: 150,
      width: 200,
    },
    {
      label: t('授权的IP'),
      field: 'ips',
      showOverflowTooltip: true,
      render: ({ data }: { data: RowData }) => {
        const ipList = data.ips.replace(/,/g, '\n')
        return (
          <span>
            { data.ips || '--' }
            <db-icon
              is-show={data.ips.length > 0}
              class="copy-btn"
              type="copy"
              onClick={() => execCopy(ipList, t('复制成功，共n条', { n: ipList.split('\n').length }))} />
          </span>
        )
      }
    },
  ]);
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
