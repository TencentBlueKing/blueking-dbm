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
    :data="dataList"
    row-key="immute_domain">
    <TicketInfoTableColumn
      col-key="immute_domain"
      :get-copy-value="(row: RowData) => row.immute_domain"
      :title="t('目标分片集群')" />
    <TicketInfoTableColumn
      col-key="target_spec"
      :title="t('目标资源规格')">
      <template #default="{ row }: { row: RowData }">
        <span>{{ row.target_spec || '--' }}</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="shard_node_count"
      :title="t('目标Shard节点数')" />
    <TicketInfoTableColumn
      col-key="shard_machine_group"
      :title="t('目标机器组数')" />
    <TicketInfoTableColumn
      col-key="shards_num"
      :title="t('分片数')" />
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Mongodb.ScaleUpdown>;
  }

  type RowData = UnwrapRef<typeof dataList>[number];

  defineOptions({
    name: TicketTypes.MONGODB_SCALE_UPDOWN,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const dataList = computed(() => {
    const { clusters, infos, specs } = props.ticketDetails.details;
    return infos.map((item) => ({
      immute_domain: clusters[item.cluster_id].immute_domain,
      shard_machine_group: item.shard_machine_group,
      shard_node_count: item.shard_node_count,
      shards_num: item.shards_num,
      target_spec: specs[item.resource_spec.mongodb.spec_id].name,
    }));
  });
</script>
