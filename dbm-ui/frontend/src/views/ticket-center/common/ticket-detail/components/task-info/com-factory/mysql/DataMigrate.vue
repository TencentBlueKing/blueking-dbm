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

  import type { MysqlDataMigrateDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<MysqlDataMigrateDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = computed(() => {
    const {
      clusters,
      infos,
    } = props.ticketDetails.details;

    return infos.map(item => ({
      cloneType: item.data_schema_grant,
      dbNameList: item.db_list,
      sourceCluster: clusters[item.source_cluster].immute_domain,
      targetClusters: item.target_clusters.map(id => clusters[id].immute_domain),
    }));
  });

  const cloneTypeMap: Record<string, string> = {
    'data,schema': t('克隆表结构和数据'),
    'schema': t('克隆表结构'),
  }

  const columns = [
    {
      label: t('源集群'),
      width: 220,
      field: 'sourceCluster',
      fixed: 'left'
    },
    {
      label: t('目标集群'),
      field: 'targetClusters',
      minWidth: 300,
      render: ({ cell }: {cell: string[]}) => (
        <span>
          {cell.join(',')}
        </span>
      ),
    },
    {
      label: t('克隆类型'),
      field: 'cloneType',
      minWidth: 300,
      render: ({ cell }: {cell: string}) => <span>{cloneTypeMap[cell] || '--'}</span>,
    },
    {
      label: t('最终DB名'),
      field: 'dbNameList',
      minWidth: 200,
      render: ({ cell }: {cell: string[]}) => (
        <span>
          {cell.join(',')}
        </span>
      ),
    },
  ];
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
