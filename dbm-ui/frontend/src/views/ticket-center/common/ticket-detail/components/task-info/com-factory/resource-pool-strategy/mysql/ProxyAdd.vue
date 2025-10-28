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
  <InfoList>
    <InfoItem :label="t('主机选择方式')">
      {{ ticketDetails.details.source_type === SourceType.RESOURCE_AUTO ? t('资源池自动匹配') : t('资源池手动选择') }}
    </InfoItem>
  </InfoList>
  <InfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_ids">
    <InfoTableColumn
      col-key="cluster_ids"
      fixed="left"
      :get-copy-value="
        (item: RowData) => item.cluster_ids.map((clusterId) => ticketDetails.details.clusters[clusterId].immute_domain)
      "
      :min-width="250"
      :title="t('目标集群')">
      <template #default="{ row: data }: { row: RowData }">
        <div
          v-for="clusterId in data.cluster_ids"
          :key="clusterId"
          style="line-height: 20px">
          {{ ticketDetails.details.clusters[clusterId].immute_domain }}
        </div>
      </template>
    </InfoTableColumn>
    <template v-if="ticketDetails.details.source_type === SourceType.RESOURCE_AUTO">
      <InfoTableColumn
        col-key="spec_id"
        :min-width="120"
        :title="t('规格')">
        <template #default="{ row: data }: { row: RowData }">
          {{ ticketDetails.details.specs?.[data.resource_spec.new_proxy.spec_id]?.name || '--' }}
        </template>
      </InfoTableColumn>
      <InfoTableColumn
        col-key="label_names"
        :min-width="200"
        :title="t('资源标签')">
        <template #default="{ row: data }: { row: RowData }">
          <template v-if="data.resource_spec.new_proxy?.label_names?.length">
            <BkTag
              v-for="item in data.resource_spec.new_proxy.label_names"
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
      </InfoTableColumn>
    </template>
    <template v-if="ticketDetails.details.source_type === SourceType.RESOURCE_MANUAL">
      <InfoTableColumn
        col-key="new_proxy_ip"
        :min-width="120"
        :title="t('新Proxy主机')">
        <template #default="{ row: data }: { row: RowData }">
          {{ data.resource_spec.new_proxy.hosts?.[0]?.ip || '--' }}
        </template>
      </InfoTableColumn>
    </template>
  </InfoTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';
  import { SourceType } from '@services/types';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';
  import InfoTable, { InfoTableColumn } from '../../components/info-table/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.ProxyAdd>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_PROXY_ADD,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
