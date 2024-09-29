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
    <BkTableColumn :label="t('源集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.src_cluster].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('目标集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.dst_cluster].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('迁移 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="dbName in data.db_list"
          :key="dbName">
          {{ dbName }}
        </BkTag>
        <span v-if="data.db_list.length < 1">--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('忽略 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="dbName in data.ignore_db_list"
          :key="dbName">
          {{ dbName }}
        </BkTag>
        <span v-if="data.ignore_db_list.length < 1">--</span>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('迁移后 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag
          v-for="item in data.rename_infos"
          :key="item.db_name">
          {{ item.target_db_name }}
        </BkTag>
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Sqlserver } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Sqlserver.DataMigrate>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.SQLSERVER_DATA_MIGRATE,
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
