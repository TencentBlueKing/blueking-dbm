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
    <InfoItem :label="t('闪回方式:')">
      {{ ticketDetails.details.flashback_type === 'RECORD_FLASHBACK' ? t('记录级闪回') : t('库表闪回') }}
    </InfoItem>
  </InfoList>
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
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
        {{ dayjs(data.start_time).format('YYYY-MM-DD HH:mm:ss ZZ') }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('截止时间')"
      :min-width="250">
      <template #default="{ data }: { data: RowData }">
        {{ dayjs(data.end_time).format('YYYY-MM-DD HH:mm:ss ZZ') }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('目标库')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.databases" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      v-if="isTableFlashback"
      :label="t('忽略库')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.databases_ignore" />
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('目标表')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.tables" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      v-if="isTableFlashback"
      :label="t('忽略表')">
      <template #default="{ data }: { data: RowData }">
        <TagBlock :data="data.tables_ignore" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      v-if="isRecordFlashback"
      :label="t('待闪回记录')"
      :min-width="300"
      :show-overflow="false">
      <template #default="{ data }: { data: RowData }">
        <div style="line-height: 26px; white-space: pre">{{ data.rows_filter }}</div>
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList v-if="isRecordFlashback">
    <InfoItem :label="t('覆盖原始数据:')">
      {{ ticketDetails.details.infos[0].direct_write_back ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import dayjs from 'dayjs';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.FlashBack>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_FLASHBACK,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const isTableFlashback = computed(() => props.ticketDetails.details.flashback_type === 'TABLE_FLASHBACK');
  const isRecordFlashback = computed(() => props.ticketDetails.details.flashback_type === 'RECORD_FLASHBACK');
</script>
