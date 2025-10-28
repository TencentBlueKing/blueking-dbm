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
  <InfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_id">
    <InfoTableColumn
      col-key="cluster_id"
      fixed="left"
      :get-copy-value="(item: RowData) => ticketDetails.details.clusters[item.cluster_id].immute_domain"
      :min-width="250"
      :title="t('集群')">
      <template #default="{ row: data }: { row: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="truncate_data_type"
      :title="t('清档类型')"
      :width="220">
      <template #default="{ row: data }: { row: RowData }">
        {{ truncateDataTypes[data.truncate_data_type as keyof typeof truncateDataTypes] }}
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="db_patterns"
      :title="t('指定 DB 名')">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.db_patterns" />
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="ignore_dbs"
      :title="t('忽略 DB 名')">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.ignore_dbs" />
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="table_patterns"
      :title="t('指定表名')">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.table_patterns" />
      </template>
    </InfoTableColumn>
    <InfoTableColumn
      col-key="ignore_tables"
      :title="t('忽略表名')">
      <template #default="{ row: data }: { row: RowData }">
        <TagBlock :data="data.ignore_tables" />
      </template>
    </InfoTableColumn>
  </InfoTable>
  <InfoList>
    <InfoItem :label="t('安全模式')">
      {{ !ticketDetails.details.infos[0].force ? t('是') : t('否') }}
    </InfoItem>
    <InfoItem :label="t('删除备份库时间:')">
      {{
        ticketDetails.details.clear_mode?.mode === 'timer'
          ? t('n天后', {
              n: ticketDetails.details.clear_mode.days,
            })
          : t('手动')
      }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import TagBlock from '@components/tag-block/Index.vue';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';
  import InfoTable, { InfoTableColumn } from '../../components/info-table/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.TruncateData>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  const { t } = useI18n();

  const truncateDataTypes = {
    drop_database: t('删除整库_dropdatabase'),
    drop_table: t('清除表数据和结构_droptable'),
    truncate_table: t('清除表数据_truncatetable'),
  };
</script>
