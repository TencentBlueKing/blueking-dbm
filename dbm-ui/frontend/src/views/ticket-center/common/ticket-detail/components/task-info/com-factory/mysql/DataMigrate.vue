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
    row-key="source_cluster">
    <TableColumn
      col-key="source_cluster"
      fixed="left"
      :min-width="240"
      :title="t('源集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.source_cluster].immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="target_clusters"
      :min-width="240"
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="clusterId in row.target_clusters"
          :key="clusterId">
          {{ ticketDetails.details.clusters[clusterId].immute_domain }}
        </div>
      </template>
    </TableColumn>
    <TableColumn
      col-key="data_schema_grant"
      :title="t('克隆类型')">
      <template #default="{ row }: { row: RowData }">
        {{ row.data_schema_grant === 'schema' ? t('克隆表结构') : t('克隆表结构和数据') }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="clone_db_list"
      :min-width="180"
      :title="t('克隆DB名')">
      <template #default="{ row }: { row: RowData }">
        <BkTag
          v-for="item in row.clone_db_list"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="row.clone_db_list.length < 1">--</span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="ignore_db_list"
      :min-width="180"
      :title="t('忽略DB名')">
      <template #default="{ row }: { row: RowData }">
        <BkTag
          v-for="item in row.ignore_db_list"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="row.ignore_db_list.length < 1">--</span>
      </template>
    </TableColumn>
    <TableColumn
      col-key="db_list"
      :min-width="180"
      :title="t('最终DB名')">
      <template #default="{ row }: { row: RowData }">
        <BkTag
          v-for="item in row.db_list"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="row.db_list.length < 1">--</span>
      </template>
    </TableColumn>
  </PrimaryTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mysql.DataMigrate>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MYSQL_DATA_MIGRATE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
