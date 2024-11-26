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
  <BkTable
    :data="tableData"
    show-overflow-tooltip>
    <BkTableColumn
      field="cluster_ids"
      :label="t('集群ID')">
      <template #default="{ data }: { data: RowData }">
        {{ data.id }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="immute_domain"
      :label="t('集群名称')">
      <template #default="{ data }: { data: RowData }">
        <div
          v-bk-tooltips="{
            content: `${t('域名')}：${ticketDetails.details.clusters[data.id].immute_domain}
            ${ticketDetails.details.clusters[data.id].name ? `${'集群别名'}：${ticketDetails.details.clusters[data.id].name}` : null}
          `,
            allowHTML: true,
          }"
          class="cluster-name">
          <span>{{ ticketDetails.details.clusters[data.id].immute_domain }}</span>
          <br />
          <span
            v-if="ticketDetails.details.clusters[data.id].name"
            class="cluster-name-alias">
            {{ ticketDetails.details.clusters[data.id].name }}
          </span>
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="cluster_type_name"
      :label="t('集群类型')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.id].cluster_type_name }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="ts">
  import { type UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import type { DetailClusters } from '@services/model/ticket/details/common';
  import TicketModel from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<{
      clusters: DetailClusters;
      cluster_ids: number[];
    }>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = computed(() => props.ticketDetails.details.cluster_ids.map((id) => ({ id })));

  type RowData = UnwrapRef<typeof tableData>[number];
</script>

<style lang="less" scoped>
  .cluster-name {
    padding: 8px 0;
    line-height: 16px;

    .cluster-name-alias {
      color: @light-gray;
    }
  }
</style>
