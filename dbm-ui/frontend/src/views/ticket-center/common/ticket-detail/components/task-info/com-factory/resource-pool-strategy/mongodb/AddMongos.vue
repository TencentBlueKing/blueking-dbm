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
      fixed="left"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.cluster_id].immute_domain"
      :min-width="250"
      :title="t('目标分片集群')">
      <template #default="{row}: {row: RowData}">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="current_mongos_num"
      :title="t('当前数量（台）')"
      :width="120">
      <template #default="{row}: {row: RowData}">
        {{ row.current_mongos_num || '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="resource_spec_count"
      :title="t('扩容数量（台）')"
      :width="120">
      <template #default="{row}: {row: RowData}">
        {{ row.resource_spec.mongos.count }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="final_spec_count"
      :title="t('最终数量（台）')"
      :width="120">
      <template #default="{row}: {row: RowData}">
        {{ row.current_mongos_num ? row.current_mongos_num + row.resource_spec.mongos.count : '--' }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="spec_id"
      :title="t('扩容规格')"
      :width="120">
      <template #default="{row}: {row: RowData}">
        {{ ticketDetails.details.specs[row.resource_spec.mongos.spec_id].name }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row }: { row: RowData }">
        <template v-if="row.resource_spec.mongos?.label_names?.length">
          <DbTag
            v-for="item in row.resource_spec.mongos.label_names"
            :key="item">
            {{ item }}
          </DbTag>
        </template>
        <DbTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </DbTag>
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mongodb.ResourcePool.AddMongos>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.MONGODB_ADD_MONGOS,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
