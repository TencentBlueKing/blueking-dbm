<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    ellipsis
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="spider_ip_list"
      :get-copy-value="(row: RowData) => (row.spider_ip_list || []).map((item) => item.ip)"
      :min-width="180"
      :title="t('目标 Spider 实例')">
      <template #default="{ row: data }: { row: RowData }">
        <span v-if="!data.spider_ip_list?.length">--</span>
        <p
          v-for="item in data.spider_ip_list"
          v-else
          :key="item.ip">
          {{ item.ip }}
        </p>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="rebuild_spider_role"
      :min-width="140"
      :title="t('角色')">
      <template #default="{ row: data }: { row: RowData }">
        <span>{{ roleLabelMap[data.rebuild_spider_role] || data.rebuild_spider_role || '--' }}</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_id"
      :min-width="220"
      :title="t('所属集群')">
      <template #default="{ row: data }: { row: RowData }">
        <span>{{ ticketDetails.details.clusters?.[data.cluster_id]?.immute_domain || '--' }}</span>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.SpiderRebuild>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_REBUILD,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const roleLabelMap: Record<string, string> = {
    spider_master: 'Spider Master',
    spider_mnt: 'Spider mnt',
    spider_slave: 'Spider Slave',
  };
</script>
