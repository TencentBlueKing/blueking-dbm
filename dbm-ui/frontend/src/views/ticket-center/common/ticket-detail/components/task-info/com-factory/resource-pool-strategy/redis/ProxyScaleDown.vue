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
    <InfoItem :label="t('缩容方式')">
      {{ ticketDetails.details.shrink_type === 'HOST' ? t('指定主机缩容') : t('指定数量缩容') }}
    </InfoItem>
  </InfoList>
  <BkTable
    v-if="ticketDetails.details.shrink_type === 'HOST'"
    :data="tableData"
    :show-overflow="false">
    <BkTableColumn
      field="ip"
      :label="t('目标主机')"
      :min-width="200" />
    <BkTableColumn
      field="domain"
      :label="t('关联集群')"
      :min-width="250" />
    <BkTableColumn
      field="online_switch_type"
      :label="t('切换模式')"
      :min-width="150" />
  </BkTable>
  <BkTable
    v-else
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      :label="t('目标集群')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters?.[data.cluster_id]?.immute_domain || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('架构版本')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters?.[data.cluster_id]?.cluster_type_name || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('当前数量(台)')"
      :min-width="100">
      <template #default="{ data }: { data: RowData }">
        {{ data.old_nodes.proxy_reduced_hosts.length + data.target_proxy_count }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('缩容数量(台)')"
      :min-width="100">
      <template #default="{ data }: { data: RowData }">
        {{ data.old_nodes.proxy_reduced_hosts.length }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="target_proxy_count"
      :label="t('剩余数量(台)')"
      :min-width="100" />
    <BkTableColumn :label="t('切换模式')">
      <template #default="{ data }: { data: RowData }">
        {{ data.online_switch_type === 'no_confirm' ? t('无需确认') : t('需人工确认') }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.ResourcePool.ProxyScaleDown>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.REDIS_PROXY_SCALE_DOWN,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  interface HostTableRow {
    domain: string;
    ip: string;
    online_switch_type: string;
  }

  const tableData = computed(() => {
    const { clusters, infos } = props.ticketDetails.details;
    const data = infos.reduce<HostTableRow[]>((acc, item) => {
      item.old_nodes.proxy_reduced_hosts.forEach((host) => {
        acc.push({
          domain: clusters[item.cluster_id]?.immute_domain || '--',
          ip: host.ip,
          online_switch_type: item.online_switch_type === 'no_confirm' ? t('无需确认') : t('需人工确认'),
        });
      });
      return acc;
    }, []);
    return data;
  });
</script>
