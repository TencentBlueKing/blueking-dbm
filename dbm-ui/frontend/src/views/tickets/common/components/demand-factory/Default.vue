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
    v-if="tableData.length > 0"
    :columns="columns"
    :data="tableData" />
  <div
    v-else
    class="json-display">
    {{ JSON.stringify(ticketDetails) }}
  </div>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import type { DetailClusters } from '@services/model/ticket/details/common';
  import TicketModel from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<{
      clusters?: DetailClusters;
      infos?: {
        cluster_id: number;
      }[];
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const columns = [
    {
      label: t('集群名称'),
      field: 'immute_domain',
      showOverflowTooltip: true,
    },
  ];

  const { clusters, infos } = props.ticketDetails.details;

  const tableData = infos
    ? infos.map((item) => ({
        immute_domain: clusters ? clusters[item.cluster_id].immute_domain : '--',
      }))
    : [];
</script>
<style lang="less" scoped>
  .json-display {
    overflow-y: auto;
  }
</style>
