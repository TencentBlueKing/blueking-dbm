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
  <PrimaryTable
    :data="ticketDetails.details.infos"
    ellipsis
    row-key="cluster_id">
    <TableColumn
      :min-width="200"
      :title="t('目标集群')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      :min-width="120"
      :title="t('目标规格')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.specs?.[data.resource_spec.spider_slave_ip_list.spec_id]?.name || '--' }}
      </template>
    </TableColumn>
    <TableColumn
      :min-width="120"
      :title="t('部署台数')">
      <template #default="{ row: data }: { row: RowData }">
        {{ data.resource_spec.spider_slave_ip_list.count }}
      </template>
    </TableColumn>
    <TableColumn
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row: data }: { row: RowData }">
        <template v-if="data.resource_spec.spider_slave_ip_list?.label_names?.length">
          <BkTag
            v-for="item in data.resource_spec.spider_slave_ip_list.label_names"
            :key="item">
            {{ item }}
          </BkTag>
        </template>
        <BkTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </BkTag>
      </template>
    </TableColumn>
  </PrimaryTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.SpiderSlaveApply>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_SLAVE_APPLY,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
