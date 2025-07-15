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
    <BkTableColumn :label="t('集群类型')">
      <template #default="{ data }: { data: { cluster_id: number } }">
        {{ ticketDetails.details.clusters?.[data.cluster_id]?.cluster_type_name || '--' }}
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('下发配置')">
      {{ ticketDetails.details.with_push_config ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('推送二进制文件')">
      {{ ticketDetails.details.with_deploy_binary ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('CC 标准化')">
      {{ ticketDetails.details.with_cc_standardize ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ClusterStandardize>;
  }

  defineOptions({
    name: TicketTypes.MYSQL_CLUSTER_STANDARDIZE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
