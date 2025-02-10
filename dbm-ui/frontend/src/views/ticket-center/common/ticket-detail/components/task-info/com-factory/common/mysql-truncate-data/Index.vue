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
    <BkTableColumn :label="t('集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('清档类型')">
      <template #default="{ data }: { data: RowData }">
        {{ truncateDataTypes[data.truncate_data_type as keyof typeof truncateDataTypes] }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('指定 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.db_patterns"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="data.db_patterns.length < 1">--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('忽略 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.ignore_dbs"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="data.ignore_dbs.length < 1">--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('指定表名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.table_patterns"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="data.table_patterns.length < 1">--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('忽略表名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.ignore_tables"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="data.ignore_tables.length < 1">--</span>
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('安全模式:')">
      {{ !ticketDetails.details.infos[0].force ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.TruncateData>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  const { t } = useI18n();

  const truncateDataTypes = {
    truncate_table: t('清除表数据_truncatetable'),
    drop_table: t('清除表数据和结构_droptable'),
    drop_database: t('删除整库_dropdatabase'),
  };
</script>
