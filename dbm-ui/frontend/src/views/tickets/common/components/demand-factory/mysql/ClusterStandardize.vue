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

  import type { MysqlClusterStandardizeDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';

  import { useGlobalBizs } from '@stores';

  import { ClusterTypes } from '@common/const';

  import DbStatus from '@components/db-status/index.vue';

  interface Props {
    ticketDetails: TicketModel<MysqlClusterStandardizeDetails>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { getBizById } = useGlobalBizs();

  const clusterTypeMap: Record<string, string> = {
    [ClusterTypes.TENDBHA]: t('主从'),
    [ClusterTypes.TENDBSINGLE]: t('单节点'),
  }

  const statusMap: Record<string, {
    text: string;
    theme: 'success' | 'danger'
  }> = {
    normal: {
      text: t('正常'),
      theme: 'success'
    },
    abnormal: {
      text: t('异常'),
      theme: 'danger'
    },
  }

  const columns = [
    {
      label: t('目标集群'),
      width: 220,
      field: 'immute_domain',
    },
    {
      label: t('集群类型'),
      field: 'cluster_type',
      render: ({ cell }: {cell: string}) => <span>{ clusterTypeMap[cell] || cell }</span>,
    },
    {
      label: t('归属业务'),
      field: 'bk_biz_name',
    },
    {
      label: t('状态'),
      field: 'status',
      render: ({ cell }: {cell: string}) => <DbStatus theme={statusMap[cell].theme}>{ statusMap[cell].text }</DbStatus>
    },
  ];

  const tableData = computed(() => {
    const {
      clusters,
      infos,
    } = props.ticketDetails.details;

    return infos.cluster_ids.map(id => ({
      ...clusters[id],
      bk_biz_name: getBizById(clusters[id].bk_biz_id)?.name || ''
    }));
  });
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
</style>
