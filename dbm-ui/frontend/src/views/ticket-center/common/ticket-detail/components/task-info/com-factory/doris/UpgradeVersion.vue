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
    <InfoItem :label="t('目标集群')">
      {{ clusterDomain }}
    </InfoItem>
    <InfoItem :label="t('当前版本')">
      {{ ticketDetails.details.clusters?.[ticketDetails.details.cluster_id]?.major_version || '--' }}
    </InfoItem>
    <InfoItem :label="t('目标版本')">
      {{ ticketDetails.details.new_version }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Doris } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Doris.UpgradeVersion>;
  }

  defineOptions({
    name: TicketTypes.DORIS_UPGRADE,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const clusterDomain = computed(() => {
    const { cluster_id: clusterId, clusters = {} } = props.ticketDetails.details;
    return clusters[clusterId]?.immute_domain ?? '--';
  });
</script>
