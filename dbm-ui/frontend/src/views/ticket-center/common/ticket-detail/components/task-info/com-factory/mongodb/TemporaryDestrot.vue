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

  import type { TicketDetails } from '@services/types/ticket';

  interface TemporaryDestroyDeatils {
    clusters: Record<
      number,
      {
        alias: string;
        bk_biz_id: number;
        bk_cloud_id: number;
        cluster_type: string;
        cluster_type_name: string;
        creator: string;
        db_module_id: number;
        disaster_tolerance_level: string;
        id: number;
        immute_domain: string;
        major_version: string;
        name: string;
        phase: string;
        region: string;
        status: string;
        tag: {
          bk_biz_id: number;
          name: string;
          type: string;
        }[];
        time_zone: string;
        updater: string;
      }
    >;
    cluster_ids: number[];
  }

  interface Props {
    ticketDetails: TicketDetails<TemporaryDestroyDeatils>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      label: t('临时集群名称'),
      field: 'name',
      showOverflowTooltip: false,
    },
  ];

  const dataList = computed(() => {
    const { clusters, cluster_ids: clusterIds } = props.ticketDetails.details;
    return clusterIds.map((id) => ({
      name: clusters[id].name,
    }));
  });
</script>
