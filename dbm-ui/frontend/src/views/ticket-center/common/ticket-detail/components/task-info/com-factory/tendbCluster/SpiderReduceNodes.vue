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
    <BkTableColumn :label="t('目标集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('缩容节点类型')">
      <template #default="{ data }: { data: RowData }">
        {{ data.reduce_spider_role === 'spider_master' ? 'Master' : 'Slave' }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('主机选择方式')">
      <template #default="{ data }: { data: RowData }">
        <template v-if="data.spider_reduced_hosts">
          <div
            v-for="item in data.spider_reduced_hosts"
            :key="item.bk_host_id">
            {{ item.ip }}
          </div>
        </template>
        <span v-else>{{ t('自动匹配') }}</span>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('缩容数量(台)')">
      <template #default="{ data }: { data: RowData }">
        {{ data.spider_reduced_hosts ? data.spider_reduced_hosts.length : data.spider_reduced_to_count }}
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('忽略业务连接:')">
      {{ ticketDetails.details.is_safe ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.SpiderReduceNodes>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_REDUCE_NODES,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  type RowData = Props['ticketDetails']['details']['infos'][number];
</script>
