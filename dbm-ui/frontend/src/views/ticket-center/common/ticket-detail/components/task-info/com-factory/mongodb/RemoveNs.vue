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
  <PrimaryTable
    :data="ticketDetails.details.infos"
    row-key="cluster_ids">
    <TableColumn
      col-key="cluster_ids"
      fixed="left"
      :min-width="250"
      :title="t('目标集群')">
      <template #default="{row:data}: {row: RowData}">
        <div
          v-for="item in data.cluster_ids"
          :key="item">
          {{ ticketDetails.details.clusters[item].immute_domain }}
        </div>
      </template>
    </TableColumn>
    <TableColumn
      col-key="drop_type"
      :title="t('集群类型')"
      :width="150">
      <template #default="{row:data}: {row: RowData}">
        {{ ticketDetails.details.clusters[data.cluster_ids[0]].cluster_type_name }}
      </template>
    </TableColumn>
    <!-- <TableColumn
      col-key="drop_type"
      :title="t('清档类型')"
      :width="270">
      <template #default="{row:data}: {row: RowData}">
        {{ data.drop_type === 'drop_collection' ? t('直接删除表') : t('将表暂时重命名，用于需要快速恢复的情况') }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="drop_index"
      :title="t('索引处理')"
      :width="90">
      <template #default="{row:data}: {row: RowData}">
        {{ data.drop_index ? t('删除索引') : t('保留索引') }}
      </template>
    </TableColumn> -->
    <TableColumn
      col-key="db_patterns"
      :min-width="120"
      :title="t('指定 DB 名')">
      <template #default="{row:data}: {row: RowData}">
        <TagBlock :data="data.ns_filter.db_patterns" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="ignore_dbs"
      :min-width="120"
      :title="t('忽略 DB 名')">
      <template #default="{row:data}: {row: RowData}">
        <TagBlock :data="data.ns_filter.ignore_dbs" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="table_patterns"
      :min-width="120"
      :title="t('指定表名')">
      <template #default="{row:data}: {row: RowData}">
        <TagBlock :data="data.ns_filter.table_patterns" />
      </template>
    </TableColumn>
    <TableColumn
      col-key="ignore_tables"
      :min-width="120"
      :title="t('忽略表名')">
      <template #default="{row:data}: {row: RowData}">
        <TagBlock :data="data.ns_filter.ignore_tables" />
      </template>
    </TableColumn>
  </PrimaryTable>
  <!-- <InfoList>
    <InfoItem :label="t('忽略业务连接')">
      {{ ticketDetails.details.is_safe ? t('否') : t('是') }}
    </InfoItem>
  </InfoList> -->
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  // import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mongodb.RemoveNs>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_REMOVE_NS,
    inheritAttrs: false,
  });

  defineProps<Props>();

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const { t } = useI18n();
</script>
