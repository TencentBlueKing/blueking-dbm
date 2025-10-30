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
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_ids">
    <TicketInfoTableColumn
      col-key="cluster_ids"
      :get-copy-value="(row: RowData) => row.cluster_ids.map(clusterId => ticketDetails.details.clusters[clusterId].immute_domain)"
      :min-width="220"
      :title="t('集群')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="item in row.cluster_ids"
          :key="item">
          {{ ticketDetails.details.clusters[item].immute_domain }}
        </div>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="drop_type"
      :title="t('集群类型')"
      :width="150">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_ids[0]].cluster_type_name }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="db_patterns"
      :title="t('备份DB名')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ns_filter.db_patterns" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="ignore_dbs"
      :title="t('忽略DB名')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ns_filter.ignore_dbs" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="table_patterns"
      :title="t('备份表名')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ns_filter.table_patterns" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="ignore_tables"
      :title="t('忽略表名')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ns_filter.ignore_tables" />
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
  <InfoList>
    <InfoItem :label="t('备份保存时间')">
      {{ fileTagMap[ticketDetails.details.file_tag] }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  type RowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Mongodb.Backup>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_BACKUP,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const fileTagMap: Record<string, string> = {
    a_year_backup: t('1年'),
    forever_backup: t('3年'),
    half_year_backup: t('6个月'),
    normal_backup: t('25天'),
  };
</script>
