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

  import type {
    MysqlOpenAreaDetails,
    TicketDetails,
  } from '@services/types/ticket';

  interface Props {
    ticketDetails: TicketDetails<MysqlOpenAreaDetails>
  }

  interface RowData {
    targetCluster: string,
    newDb: string,
    tbStruct: string[],
    tbData: string[],
    ips: string[],
    rules: string[],
  }

  const props = defineProps<Props>();

  const clustersMap = props.ticketDetails.details.clusters;
  const rulesSetMap = props.ticketDetails.details.rules_set.reduce((results, item) => {
    // eslint-disable-next-line no-param-reassign
    results[item.target_instances[0]] = item;
    return results;
  }, {} as Record<string, MysqlOpenAreaDetails['rules_set'][number]>);

  const tableData = props.ticketDetails.details.config_data.map((item) => {
    const clusterName = clustersMap[item.cluster_id].immute_domain;
    return ({
      targetCluster: clusterName,
      newDb: item.execute_objects[0].target_db,
      tbStruct: item.execute_objects[0].schema_tblist,
      tbData: item.execute_objects[0].data_tblist,
      ips: rulesSetMap[clusterName].source_ips,
      rules: rulesSetMap[clusterName].account_rules.map(item => item.dbname),
    });
  });

  const { t } = useI18n();

  const columns = [
    {
      label: t('目标集群'),
      minWidth: 150,
      width: 200,
      field: 'targetCluster',
    },
    {
      label: t('新 DB'),
      field: 'newDb',
      width: 120,
    },
    {
      label: t('表结构'),
      field: 'tbStruct',
      minWidth: 120,
      render: ({ data }: {data: RowData}) => (
        <span>
          {data.tbStruct.join(',')}
        </span>
      ),
    },
    {
      label: t('表数据'),
      field: 'tbData',
      minWidth: 120,
      render: ({ data }: {data: RowData}) => (
        <span>
          {data.tbData.join(',')}
        </span>
      ),
    },
    {
      label: t('授权IP'),
      field: 'ips',
      render: ({ data }: {data: RowData}) => (
        <span>
          {data.ips.join(',')}
        </span>
      ),
    },
    {
      label: t('授权规则'),
      field: 'rules',
      render: ({ data }: {data: RowData}) => (
        <span>
          {data.rules.join(',')}
        </span>
      ),
    },
  ];
</script>
