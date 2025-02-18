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
      fixed="left"
      :label="t('目标集群')"
      :min-width="220">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('回档时间')"
      :min-width="250">
      <template #default="{ data }: { data: RowData }">
        {{ utcDisplayTime(data.start_time) }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('截止时间')"
      :min-width="250">
      <template #default="{ data }: { data: RowData }">
        {{ utcDisplayTime(data.end_time) }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('目标库')"
      :min-width="120">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.databases" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('忽略库')"
      :min-width="120">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.databases_ignore" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('目标表')"
      :min-width="120">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.tables" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('忽略表')"
      :min-width="120">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.tables_ignore" />
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import { utcDisplayTime } from '@utils';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.FlashBack>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_FLASHBACK,
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
