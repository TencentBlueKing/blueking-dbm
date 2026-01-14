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
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="cluster_id"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.cluster_id].immute_domain"
      :min-width="350"
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_type_name"
      :title="t('集群类型')"
      :width="130">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].cluster_type_name }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="db_patterns"
      :min-width="200"
      :title="t('DB 名')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ns_filter.db_patterns" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="ignore_dbs"
      :min-width="200"
      :title="t('忽略DB名')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ns_filter.ignore_dbs" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="table_patterns"
      :min-width="200"
      :title="t('表名')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ns_filter.table_patterns" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="ignore_tables"
      :min-width="200"
      :title="t('忽略表名')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock :data="row.ns_filter.ignore_tables" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="query"
      :min-width="380"
      :title="t('查询条件')">
      <template #default="{ row }: { row: RowData }">
        <span v-if="row.export_options.query">{{ row.export_options.query }}</span>
        <span v-else>--</span>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
  <InfoList>
    <InfoItem :label="t('导出格式')">
      {{ ticketDetails.details.infos[0]?.export_options?.format === 'bson' ? 'BSON' : 'JSON' }}
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
    ticketDetails: TicketModel<Mongodb.DataExport>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_DATA_EXPORT,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
