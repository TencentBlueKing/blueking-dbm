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
      field="cluster_ids"
      fixed="left"
      :label="t('目标集群')"
      :min-width="250">
      <template #default="{data}: {data: RowData}">
        <div
          v-for="item in data.cluster_ids"
          :key="item">
          {{ ticketDetails.details.clusters[item].immute_domain }}
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="drop_collection"
      :label="t('清档类型')"
      :width="300">
      <template #default="{data}: {data: RowData}">
        {{ data.drop_type === 'drop_collection' ? t('直接删除表') : t('将表暂时重命名，用于需要快速恢复的情况') }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="drop_index"
      :label="t('是否删除索引')">
      <template #default="{data}: {data: RowData}">
        {{ data.drop_type === 'drop_index' ? t('是') : t('否') }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="db_patterns"
      :label="t('指定 DB 名')"
      :min-width="120">
      <template #default="{data}: {data: RowData}">
        <TagBlock :data="data.ns_filter.db_patterns" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="ignore_dbs"
      :label="t('忽略 DB 名')"
      :min-width="120">
      <template #default="{data}: {data: RowData}">
        <TagBlock :data="data.ns_filter.ignore_dbs" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="table_patterns"
      :label="t('指定表名')"
      :min-width="120">
      <template #default="{data}: {data: RowData}">
        <TagBlock :data="data.ns_filter.table_patterns" />
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="ignore_tables"
      :label="t('忽略表名')"
      :min-width="120">
      <template #default="{data}: {data: RowData}">
        <TagBlock :data="data.ns_filter.ignore_tables" />
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('忽略业务连接')">
      {{ ticketDetails.details.is_safe ? t('否') : t('是') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mongodb.RemoveNs>;
  }

  defineProps<Props>();

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MONGODB_REMOVE_NS,
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
