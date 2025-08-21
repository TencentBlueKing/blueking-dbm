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
    :data="ticketDetails.details.cluster_ids.map((item) => ({ cluster_id: item }))"
    :show-overflow="false">
    <BkTableColumn :label="t('目标集群')">
      <template #default="{ data }: { data: { cluster_id: number } }">
        {{ ticketDetails.details.clusters?.[data.cluster_id]?.immute_domain || '--' }}
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('重新下发GSE配置')">
      {{ ticketDetails.details.restart_exporter ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.ClusterReinstallDbmon>;
  }

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_REINSTALL_DBMON,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
