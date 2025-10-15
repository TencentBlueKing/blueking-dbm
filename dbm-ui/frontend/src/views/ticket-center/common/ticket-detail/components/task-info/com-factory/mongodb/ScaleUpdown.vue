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
    row-key="cluster_id">
    <TableColumn
      col-key="cluster_id"
      fixed="left"
      :min-width="340"
      :title="t('目标集群')">
      <template #default="{row}: {row: RowData}">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="resource_spec"
      :min-width="120"
      :title="t('目标资源规格')">
      <template #default="{row}: {row: RowData}">
        {{ ticketDetails.details.specs[row.resource_spec.mongodb.spec_id].name }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="shard_node_count"
      :title="t('目标 Shard 节点数')">
    </TableColumn>
    <TableColumn
      col-key="shard_machine_group"
      :title="t('目标机器组数')">
    </TableColumn>
    <TableColumn
      col-key="shards_num"
      :title="t('分片数')">
    </TableColumn>
    <TableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row }: { row: RowData }">
        <template v-if="row.resource_spec.mongodb?.label_names?.length">
          <BkTag
            v-for="item in row.resource_spec.mongodb.label_names"
            :key="item">
            {{ item }}
          </BkTag>
        </template>
        <BkTag
          v-else
          theme="success">
          {{ t('通用无标签') }}
        </BkTag>
      </template>
    </TableColumn>
  </PrimaryTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  type RowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Mongodb.ScaleUpdown>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_SCALE_UPDOWN,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
