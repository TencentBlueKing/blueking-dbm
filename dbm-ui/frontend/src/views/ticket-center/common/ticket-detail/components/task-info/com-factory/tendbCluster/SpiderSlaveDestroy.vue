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
      col-key="immute_domain"
      :get-copy-value="(row: IRowData) => row.immute_domain"
      :min-width="200"
      :title="t('目标集群')">
      <template #default="{ row }: { row: IRowData }">
        {{ row.immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="reduce_spider_slave_hosts"
      :get-copy-value="(row: IRowData) => row.slaves.map((slave) => `${slave.ip}:${slave.port}`)"
      :title="t('Spider Slave 实例')">
      <template #default="{ row }: { row: IRowData }">
        <template v-if="row.slaves.length === 0">--</template>
        <p
          v-for="(slave, idx) of row.slaves"
          v-else
          :key="slave.ip || idx">
          {{ `${slave.ip}:${slave.port}` }}
        </p>
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
    ticketDetails: TicketModel<TendbCluster.SpiderSlaveDestroy>;
  }

  type IRowData = {
    cluster_id: number;
    immute_domain: string;
    slaves: Array<{
      bk_host_id: number;
      cluster_id: number;
      ip: string;
      port: number;
    }>;
  };

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_DESTROY,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = computed<IRowData[]>(() => {
    const { details } = props.ticketDetails;
    const { clusters, old_nodes } = details;
    const slaves = old_nodes?.reduce_spider_slave_hosts || [];

    // 按 cluster_id 分组
    const clusterMap = new Map<number, IRowData>();

    slaves.forEach((slave) => {
      const clusterId = slave.cluster_id;
      if (!clusterMap.has(clusterId)) {
        clusterMap.set(clusterId, {
          cluster_id: clusterId,
          immute_domain: clusters[clusterId]?.immute_domain || '',
          slaves: [],
        });
      }
      clusterMap.get(clusterId)!.slaves.push(slave);
    });

    return Array.from(clusterMap.values());
  });
</script>
