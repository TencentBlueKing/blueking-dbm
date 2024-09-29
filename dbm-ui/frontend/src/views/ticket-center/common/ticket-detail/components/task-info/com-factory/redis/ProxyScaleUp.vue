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
      <template #default="{data}: {data: IRowData}">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('架构版本')">
      <template #default="{data}: {data: IRowData}">
        {{ ticketDetails.details.clusters[data.cluster_id].cluster_type_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('扩容节点类型')"> Proxy </BkTableColumn>
    <BkTableColumn :label="t('当前规格')">
      <template #default="{data}: {data: IRowData}">
        {{ ticketDetails.details.specs[data.resource_spec.proxy.spec_id].name }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('扩容数量（台）')">
      <template #default="{data}: {data: IRowData}">
        {{ data.resource_spec.proxy.count }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.ProxyScaleUp>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_PROXY_SCALE_UP,
    inheritAttrs: false,
  });

  type IRowData = Props['ticketDetails']['details']['infos'][number];

  const { t } = useI18n();
</script>
