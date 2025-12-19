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
    <InfoItem :label="t('集群类型')">
      {{
        ticketDetails.details.clusters?.[0]?.cluster_type === ClusterTypes.SQLSERVER_SINGLE ? t('单节点') : t('主从')
      }}
    </InfoItem>
    <InfoItem :label="t('集群')">
      <p
        v-for="cluster in ticketDetails.details.clusters"
        :key="cluster.id">
        {{ cluster.immute_domain }}
      </p>
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details?.select_role"
      :label="t('查询角色')">
      {{ ticketDetails.details.select_role === 'backend_slave' ? 'Slave' : 'Master' }}
    </InfoItem>
    <InfoItem :label="t('查询 DB')">
      {{ ticketDetails.details.execute_objects?.[0]?.dbnames?.join(',') || '--' }}
    </InfoItem>
    <InfoItem :label="t('查询 SQL')">
      {{ ticketDetails.details.execute_objects?.[0]?.sql || '--' }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { ClusterTypes, TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.DataExport>;
  }

  defineOptions({
    name: TicketTypes.SQLSERVER_DATA_EXPORT,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
