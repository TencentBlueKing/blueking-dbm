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
  <BkTable :data="ticketDetails.details.recycle_hosts">
    <BkTableColumn
      field="ip"
      fixed="left"
      label="IP"
      :min-width="150" />
    <BkTableColumn
      field="bk_cloud_name"
      :label="t('管控区域')"
      :min-width="120" />
    <BkTableColumn
      field="status"
      :label="t('Agent 状态')"
      :min-width="120">
      <template #default="{ data }">
        <HostAgentStatus :data="data.status" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="city"
      :label="t('地域')"
      :min-width="120">
      <template #default="{ data }">
        {{ data.city || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="sub_zone"
      :label="t('园区')"
      :min-width="120">
      <template #default="{ data }">
        {{ data.sub_zone || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="rack_id"
      :label="t('机架')"
      :min-width="120">
      <template #default="{ data }">
        {{ data.rack_id || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="bk_os_name"
      :label="t('操作系统')"
      :min-width="120">
      <template #default="{ data }">
        {{ data.bk_os_name || '--' }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="device_class"
      :label="t('机型')"
      :min-width="120">
      <template #default="{ data }">
        {{ data.device_class || '--' }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Common } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import HostAgentStatus from '@components/host-agent-status/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Common.ResourcePoolRecycle>;
  }

  defineOptions({
    name: TicketTypes.RECYCLE_OLD_HOST,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
