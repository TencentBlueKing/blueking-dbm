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
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="cluster_id"
      fixed="left"
      :get-copy-value="(row: IRowData) => ticketDetails.details.clusters[row.cluster_id].immute_domain"
      :min-width="350"
      :title="t('目标集群')">
      <template #default="{ row }: { row: IRowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_type_name"
      :title="t('架构版本')"
      :width="200">
      <template #default="{ row }: { row: IRowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].cluster_type_name }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="capacity"
      :min-width="300"
      :title="t('当前容量')">
      <template #default="{ row }: { row: IRowData }">
        <ShardChangeCapacityCell :display-data="row.currentCapacity" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="group_num"
      :title="t('增加机器组数')"
      :width="120">
      <template #default="{ row }: { row: IRowData }">
        {{ row.resource_spec.backend_group.count }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="future_capacity"
      :min-width="400"
      :title="t('目标容量')">
      <template #default="{ row }: { row: IRowData }">
        <ShardChangeCapacityCell
          :diff-data="row.currentCapacity"
          :display-data="row.targetCapacity" />
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="label_names"
      :min-width="200"
      :title="t('资源标签')">
      <template #default="{ row: data }: { row: IRowData }">
        <template v-if="data.resource_spec.backend_group?.label_names?.length">
          <BkTag
            v-for="item in data.resource_spec.backend_group.label_names"
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
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>
<script setup lang="ts">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import ShardChangeCapacityCell from '../../common/redis/ShardChangeCapacityCell.vue';

  interface Props {
    ticketDetails: TicketModel<Redis.ResourcePool.ShardAdd>;
  }

  type IRowData = UnwrapRef<typeof dataList>[number];

  defineOptions({
    name: TicketTypes.REDIS_SHARD_ADD,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const { infos, specs } = props.ticketDetails.details;
  const dataList = infos.map((infoItem) => {
    const specInfo = specs[infoItem.resource_spec.backend_group.spec_id];
    const machineShardNum = infoItem.shard_num / infoItem.group_num;
    const currentGroupNum = infoItem.group_num - infoItem.resource_spec.backend_group.count;

    const currentCapacity = {
      capacity: infoItem.capacity,
      clusterShardNum: currentGroupNum * machineShardNum,
      groupNum: currentGroupNum,
      machineShardNum,
      spec: specInfo,
    };
    const targetCapacity = {
      capacity: infoItem.future_capacity,
      clusterShardNum: infoItem.group_num * machineShardNum,
      groupNum: infoItem.group_num,
      machineShardNum,
      spec: specInfo,
    };
    return Object.assign(infoItem, { currentCapacity, targetCapacity });
  });
</script>
