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
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      fixed="left"
      :label="t('目标集群')"
      :min-width="250">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('当前容量')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <p>{{ t('规格') }}：{{ data.prev_cluster_spec_name || '--' }}</p>
        <p>{{ t('机器组数') }}：{{ data.prev_machine_pair || '--' }}</p>
        <p>{{ t('集群分片数') }}：{{ data.cluster_shard_num || '--' }}</p>
        <p>
          {{ t('容量') }}：
          <span
            v-if="ticketDetails.details.specs[data.spec_id].capacity"
            style="font-weight: bold">
            {{ ticketDetails.details.specs[data.spec_id].capacity }} G
          </span>
          <span v-else>--</span>
        </p>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('目标容量')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <p>{{ t('规格') }}：{{ data.resource_spec.backend_group.specName || '--' }}</p>
        <p>{{ t('机器组数') }}：{{ data.resource_spec.backend_group.count || '--' }}</p>
        <p>{{ t('集群分片数') }}：{{ data.cluster_shard_num || '--' }}</p>
        <p>
          {{ t('容量') }}：
          <span
            v-if="data.resource_spec.backend_group.futureCapacity"
            style="font-weight: bold">
            {{ data.resource_spec.backend_group.futureCapacity }} G
          </span>
          <span v-else>--</span>
        </p>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('资源标签')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.resource_spec.backend_group.label_names"
          :key="item"
          :theme="labelTheme(item)">
          {{ item }}
        </BkTag>
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('数据校验')">
      {{ ticketDetails.details.need_checksum ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.NodeRebalance>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_NODE_REBALANCE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const labelTheme = (labelName: string) => (labelName === t('通用无标签') ? 'success' : '');
</script>
