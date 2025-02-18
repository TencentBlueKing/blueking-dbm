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
    <InfoItem :label="t('目标集群：')">
      {{ ticketDetails.details.clusters[ticketDetails.details.cluster_id].immute_domain }}
    </InfoItem>
    <InfoItem :label="t('目标 DB：')">
      <TagBlock :data="ticketDetails.details.databases" />
    </InfoItem>
    <InfoItem :label="t('目标表名：')">
      <TagBlock :data="ticketDetails.details.tables" />
    </InfoItem>
    <InfoItem :label="t('忽略表名：')">
      <TagBlock :data="ticketDetails.details.tables_ignore" />
    </InfoItem>
    <InfoItem :label="t('where 条件：')">
      {{ ticketDetails.details.where || '--' }}
    </InfoItem>
    <InfoItem :label="t('导出数据：')">
      <template v-if="ticketDetails.details.dump_data && ticketDetails.details.dump_schema">
        {{ t('数据和表结构') }}
      </template>
      <template v-else-if="ticketDetails.details.dump_data && !ticketDetails.details.dump_schema">
        {{ t('数据') }}
      </template>
      <template v-else>{{ t('表结构') }}</template>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import TagBlock from '@components/tag-block/Index.vue';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.DumpData>;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
