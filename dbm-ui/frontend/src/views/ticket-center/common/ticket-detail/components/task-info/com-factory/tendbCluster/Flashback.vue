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
    <InfoItem :label="t('闪回方式')">
      {{ ticketDetails.details.flashback_type === 'RECORD_FLASHBACK' ? t('记录级闪回') : t('库表闪回') }}
    </InfoItem>
  </InfoList>
  <PrimaryTable
    :data="ticketDetails.details.infos"
    row-key="cluster_id">
    <TableColumn
      col-key="cluster_id"
      fixed="left"
      :min-width="220"
      :title="t('目标集群')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="start_time"
      :min-width="250"
      :title="t('回档时间')">
      <template #default="{ row: data }: { row: RowData }">
        {{ utcDisplayTime(data.start_time) }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="end_time"
      :min-width="250"
      :title="t('截止时间')">
      <template #default="{ row: data }: { row: RowData }">
        {{ utcDisplayTime(data.end_time) }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="databases"
      :min-width="120"
      :title="t('目标库')">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.databases" />
      </template>
    </TableColumn>
    <TableColumn
      v-if="isTableFlashback"
      col-key="databases_ignore"
      :title="t('忽略库')">
      <template #default="{ row: data }: { row: RowData }">
        <BkTag
          v-for="item in data.databases_ignore"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="data.databases_ignore.length < 1">--</span>
      </template>
    </TableColumn>
    <TableColumn
      v-if="isTableFlashback"
      col-key="databases_ignore"
      :min-width="120"
      :title="t('忽略库')">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.databases_ignore" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="tables"
      :min-width="120"
      :title="t('目标表')">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.tables" />
      </template>
    </TableColumn>
    <TableColumn
      v-if="isTableFlashback"
      col-key="tables_ignore"
      :title="t('忽略表')">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.tables_ignore" />
      </template>
    </TableColumn>
    <TableColumn
      v-if="isRecordFlashback"
      col-key="rows_filter"
      :min-width="300"
      :title="t('待闪回记录')">
      <template #default="{ row: data }: { row: RowData }">
        <div style="line-height: 26px; white-space: pre">{{ data.rows_filter }}</div>
      </template>
    </TableColumn>
  </PrimaryTable>
  <InfoList v-if="isRecordFlashback">
    <InfoItem :label="t('覆盖原始数据')">
      {{ ticketDetails.details.infos[0].direct_write_back ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import { utcDisplayTime } from '@utils';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.FlashBack>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_FLASHBACK,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const isTableFlashback = computed(() => props.ticketDetails.details.flashback_type === 'TABLE_FLASHBACK');
  const isRecordFlashback = computed(() => props.ticketDetails.details.flashback_type === 'RECORD_FLASHBACK');
</script>
