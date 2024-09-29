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
    :data="dataList" />
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  export interface clustersItems {
    [key: number]: {
      alias: string;
      bk_biz_id: number;
      bk_cloud_id: number;
      cluster_type: string;
      cluster_type_name: string;
      creator: string;
      db_module_id: number;
      id: number;
      immute_domain: string;
      major_version: string;
      name: string;
      phase: string;
      region: string;
      status: string;
      time_zone: string;
      updater: string;
    };
  }

  interface Props {
    ticketDetails: TicketModel<Redis.InstanceDestroy>
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      label: t('集群ID'),
      field: 'cluster_id',
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    },
    {
      label: t('集群名称'),
      field: 'immute_domain',
      showOverflowTooltip: false,
      render: ({ data }: { data: any }) => data.immute_domain,
    },
    {
      label: t('架构版本'),
      field: 'cluster_type_name',
      render: ({ cell }: { cell: string }) => <span>{cell || '--'}</span>,
    }
  ];

  const dataList = props.ticketDetails.details.cluster_ids.reduce((prevList, clusterId) => {
    const clusters = props.ticketDetails.details.clusters[clusterId];
    return [...prevList, {
      cluster_id: clusterId,
      cluster_type_name: clusters.cluster_type_name,
      immute_domain: clusters.immute_domain,
      name: clusters.name,
    }]
  }, [] as {
    cluster_id: number,
    immute_domain: string,
    name: string,
    cluster_type_name: string,
  }[])
</script>
