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
  <InfoList>
    <InfoItem :label="t('重建对象')">{{ getRoleLabel(ticketDetails.details.infos[0]) }}</InfoItem>
  </InfoList>
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    ellipsis
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="cluster_id"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.cluster_id].immute_domain"
      :min-width="220"
      :title="t('目标集群')">
      <template #default="{ row: data }: { row: RowData }">
        <span>{{ ticketDetails.details.clusters?.[data.cluster_id]?.immute_domain || '--' }}</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="current_count"
      :min-width="120"
      :title="t('当前数量（台）')">
      <template #default="{ row: data }: { row: RowData }">
        {{ (data.old_nodes?.proxy || []).length || 0 }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="count"
      :min-width="120"
      :title="t('重建后数量（台）')">
      <template #default="{ row: data }: { row: RowData }">
        {{ getResourceSpecItem(data)?.count || 0 }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec_id"
      :min-width="160"
      :title="t('规格')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.specs?.[getResourceSpecItem(data)?.spec_id ?? 0]?.name || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row: data }: { row: RowData }">
        <template v-if="getResourceSpecItem(data)?.label_names?.length">
          <DbTag
            v-for="item in getResourceSpecItem(data)?.label_names"
            :key="item">
            {{ item }}
          </DbTag>
        </template>
        <DbTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </DbTag>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.SpiderLayerDr>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_LAYER_DR,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const getRoleLabel = (data: RowData) => {
    if (data.resource_spec?.spider_master_new_ip_list) {
      return 'Spider Master';
    }
    if (data.resource_spec?.spider_slave_new_ip_list) {
      return 'Spider Slave';
    }
    return '--';
  };

  const getResourceSpecItem = (data: RowData) =>
    data.resource_spec?.spider_master_new_ip_list || data.resource_spec?.spider_slave_new_ip_list;
</script>
