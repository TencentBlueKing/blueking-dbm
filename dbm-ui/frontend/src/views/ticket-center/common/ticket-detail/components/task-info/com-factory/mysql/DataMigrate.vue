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
  <BkTable
    :data="ticketDetails.details.infos"
    :show-overflow="false">
    <BkTableColumn
      fixed="left"
      :label="t('源集群')"
      :min-width="220">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.source_cluster].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('目标集群')"
      :min-width="220">
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="clusterId in data.target_clusters"
          :key="clusterId">
          {{ ticketDetails.details.clusters[clusterId].immute_domain }}
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('克隆类型')"
      :min-width="180">
      <template #default="{ data }: { data: RowData }">
        {{ data.data_schema_grant === 'schema' ? t('克隆表结构') : t('克隆表结构和数据') }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('迁移DB名')"
      :min-width="180">
      <template #default> -- </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('忽略DB名')"
      :min-width="180">
      <template #default> -- </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('最终DB名')"
      :min-width="180">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.db_list"
          :key="item">
          {{ item }}
        </BkTag>
        <span v-if="data.db_list.length < 1">--</span>
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mysql.DataMigrate>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_DATA_MIGRATE,
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
