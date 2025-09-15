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
      field="cluster_id"
      fixed="left"
      :label="t('目标集群')"
      :min-width="250">
      <template #default="{data}: {data: RowData}">
        {{ ticketDetails.details.clusters[data.cluster_id]?.immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="current_shards_num"
      :label="t('当前集群分片数')"
      :width="120">
    </BkTableColumn>
    <BkTableColumn
      field="add_shards_num"
      :label="t('新增集群分片数')"
      :width="120">
    </BkTableColumn>
    <BkTableColumn
      field="cluster_type"
      :label="t('最终集群分片数')"
      :width="120">
      <template #default="{data}: {data: RowData}">
        {{ data.current_shards_num + data.add_shards_num }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="single_host_shard_num"
      :label="t('单机分片数')"
      :width="120">
    </BkTableColumn>
    <BkTableColumn
      field="current_shard_nodes_num"
      :label="t('每片节点数')"
      :width="120">
    </BkTableColumn>
    <BkTableColumn
      field="resource_spec.shard_nodes.spec_id"
      :label="t('规格')"
      :min-width="200">
      <template #default="{data}: {data: RowData}">
        {{ ticketDetails.details.specs[data.resource_spec.shard_nodes.spec_id]?.name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="resource_spec.shard_nodes.count"
      :label="t('新增机器（组）')"
      :width="120">
      <template #default="{data}: {data: RowData}">
        {{ data.add_shards_num / data.single_host_shard_num }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  type RowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Mongodb.AddShard>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_ADD_SHARD,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
