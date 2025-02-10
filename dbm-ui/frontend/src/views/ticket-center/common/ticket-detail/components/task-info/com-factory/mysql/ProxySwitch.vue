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
    <InfoItem :label="t('替换类型：')">
      {{ displayInfoTypeMap[ticketDetails.details.infos[0].display_info.type] }}
    </InfoItem>
  </InfoList>
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn :label="t('目标Proxy')">
      <template #default="{ data }: { data: RowData }">
        {{ data.origin_proxy.ip }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      v-if="isHostReplace"
      :label="t('关联实例')">
      <template #default="{ data }: { data: RowData }">
        <p
          v-for="item in data.display_info.related_instances"
          :key="item">
          {{ item }}
        </p>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('关联集群')">
      <template #default="{ data }: { data: RowData }">
        <p
          v-for="item in data.display_info.related_clusters"
          :key="item">
          {{ item }}
        </p>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('新Proxy主机')">
      <template #default="{ data }: { data: RowData }">
        {{ data.target_proxy.ip }}
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('忽略业务连接：')">
      {{ ticketDetails.details.force ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ProxySwitch>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_PROXY_SWITCH,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const displayInfoTypeMap = {
    INSTANCE_REPLACE: t('实例替换'),
    HOST_REPLACE: t('整机替换'),
  };

  const isHostReplace = computed(() => props.ticketDetails.details.infos[0].display_info.type === 'HOST_REPLACE');
</script>
