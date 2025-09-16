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
  <InfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_ids">
    <InfoTableColumn
      col-key="old_nodes.proxy"
      :min-width="150"
      :title="t('目标Proxy主机')">
      <template #default="{ row: data }: { row: RowData }">
        <span v-if="!data.old_nodes?.proxy.length">--</span>
        <p
          v-for="item in data.old_nodes.proxy"
          v-else
          :key="item.ip">
          {{ item.ip }}
        </p>
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="cluster_ids"
      :min-width="250"
      :title="t('关联集群')">
      <template #default="{ row: data }: { row: RowData }">
        <div
          v-for="clusterId in data.cluster_ids"
          :key="clusterId">
          <p>
            {{ ticketDetails.details.clusters[clusterId].immute_domain }}
          </p>
        </div>
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="resource_spec.target_proxies.spec_id"
      :min-width="120"
      :title="t('目标规格')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.specs?.[data.resource_spec.target_proxies?.spec_id]?.name || '--' }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="resource_spec.target_proxies.label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row: data }: { row: RowData }">
        <template v-if="data.resource_spec.target_proxies?.label_names?.length">
          <BkTag
            v-for="item in data.resource_spec.target_proxies.label_names"
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
  </InfoTable>
  <InfoList>
    <InfoItem :label="t('检查业务连接')">
      {{ ticketDetails.details.is_safe ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';
  import InfoTable, { InfoTableColumn } from '../../components/info-table/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ResourcePool.ProxySwitch>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_PROXY_SWITCH,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
