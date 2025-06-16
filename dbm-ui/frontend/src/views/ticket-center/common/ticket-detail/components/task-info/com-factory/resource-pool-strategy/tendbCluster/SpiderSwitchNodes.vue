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
  <BkTable :data="ticketDetails.details.infos">
    <BkTableColumn
      :label="t('目标主机')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ data.spider_old_ip_list[0].ip }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('关联实例')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ `${data.spider_old_ip_list[0].ip}:${data.spider_old_ip_list[0].port}` }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('实例角色')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ data.switch_spider_role }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('关联集群')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('规格')"
      :min-width="150">
      <template #default="{ data }: { data: RowData }">
        {{
          ticketDetails.details.specs[
            data.resource_spec[`${data.switch_spider_role}_${data.spider_old_ip_list[0].ip}`].spec_id
          ].name
        }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('资源标签')"
      :min-width="200">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.resource_spec[`${data.switch_spider_role}_${data.spider_old_ip_list[0].ip}`].label_names"
          :key="item"
          :theme="labelTheme(item)">
          {{ item }}
        </BkTag>
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('检查业务连接')">
      {{ ticketDetails.details.is_safe ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ResourcePool.SpiderSwitchNodes>;
  }

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_SPIDER_SWITCH_NODES,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const labelTheme = (labelName: string) => (labelName === t('通用无标签') ? 'success' : '');
</script>
