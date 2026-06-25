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
    :data="tableData"
    ellipsis
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="spider_ip_list"
      :get-copy-value="(row: RowData) => row.old_nodes.spider_ip_list.map((item) => `${item.ip}:${item.port}`)"
      :title="t('运维节点')">
      <template #default="{ row: data }: { row: RowData }">
        <div
          v-for="item in data.old_nodes.spider_ip_list"
          :key="item.ip">
          {{ `${item.ip}:${item.port}` }}
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_id"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.cluster_id].immute_domain"
      :title="t('集群')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.SpiderMntDestroy>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_MNT_DESTROY,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = computed(() => {
    const infos = props.ticketDetails.details.infos;
    const clusterMap = new Map<number, RowData>();

    infos.forEach((info) => {
      const existing = clusterMap.get(info.cluster_id);
      if (existing) {
        existing.old_nodes.spider_ip_list.push(...info.old_nodes.spider_ip_list);
      } else {
        clusterMap.set(info.cluster_id, {
          ...info,
          old_nodes: {
            spider_ip_list: [...info.old_nodes.spider_ip_list],
          },
        });
      }
    });

    return Array.from(clusterMap.values());
  });
</script>
