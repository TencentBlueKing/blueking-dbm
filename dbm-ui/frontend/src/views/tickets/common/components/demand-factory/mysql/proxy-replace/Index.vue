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
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('替换类型') }}：</span>
      <span class="ticket-details-item-value">{{ renderData.label }}</span>
    </div>
  </div>
  <component
    :is="renderData.tableCom"
    :ticket-details="ticketDetails" />
  <div class="ticket-details-list">
    <div class="ticket-details-item">
      <span class="ticket-details-item-label">{{ t('忽略业务连接') }}：</span>
      <span class="ticket-details-item-value">{{ ticketDetails.details.force ? t('是') : t('否') }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { MySQLProxySwitchDetails } from '@services/model/ticket/details/mysql';
  import TicketModel from '@services/model/ticket/ticket';

  import { ProxyReplaceTypes } from '@views/db-manage/mysql/proxy-replace/pages/page1/Index.vue';

  import ReplaceHost from './components/ReplaceHost.vue';
  import ReplaceInstance from './components/ReplaceInstance.vue';

  interface Props {
    ticketDetails: TicketModel<MySQLProxySwitchDetails>;
  }

  const props = defineProps<Props>();

  const { t } = useI18n();

  const proxyReplaceInfo = {
    [ProxyReplaceTypes.INSTANCE_REPLACE]: {
      label: t('实例替换'),
      tableCom: ReplaceInstance,
    },
    [ProxyReplaceTypes.HOST_REPLACE]: {
      label: t('整机替换'),
      tableCom: ReplaceHost,
    },
  };

  const renderData = computed(
    () => proxyReplaceInfo[props.ticketDetails.details.infos[0].display_info.type as ProxyReplaceTypes],
  );
</script>

<style lang="less" scoped>
  @import '@views/tickets/common/styles/DetailsTable.less';
  @import '@views/tickets/common/styles/ticketDetails.less';
</style>
