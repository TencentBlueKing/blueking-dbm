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
      :label="t('目标集群')"
      :min-width="250">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('架构版本')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].cluster_type_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('缩容节点类型')"> Proxy </BkTableColumn>
    <BkTableColumn :label="t('主机选择方式')">
      <template #default="{ data }: { data: RowData }">
        {{
          data.proxy_reduced_hosts?.length ? data.proxy_reduced_hosts.map((item) => item.ip).join('\n') : t('自动匹配')
        }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('缩容数量(台)')">
      <template #default="{ data }: { data: RowData }">
        {{ data.target_proxy_count }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('切换模式')">
      <template #default="{ data }: { data: RowData }">
        {{ switchModeMap[data.online_switch_type] }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.ProxyScaleDown>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_PROXY_SCALE_DOWN,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const switchModeMap = {
    user_confirm: t('人工确认'),
    no_confirm: t('无需确认'),
  };
</script>
