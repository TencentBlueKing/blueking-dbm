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
  <BkTable :data="tableData">
    <BkTableColumn
      fixed="left"
      :label="t('目标集群')"
      :min-width="200">
      <template #default="{data}: {data: RowData}">
        <div
          v-for="item in data.cluster_ids"
          :key="item">
          {{ ticketDetails.details.clusters[item].immute_domain }}
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="cluster_type_text"
      :label="t('集群类型')"
      :min-width="150" />
    <BkTableColumn
      field="current_shard_nodes_num"
      :label="t('当前Shard的节点数')"
      :min-width="150" />
    <BkTableColumn
      :label="t('缩容至（节点数）')"
      :min-width="150">
      <template #default="{ row }: { row: RowData }">
        {{ row.current_shard_nodes_num - row.reduce_shard_nodes }}
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('忽略业务连接')">
      {{ !ticketDetails.details.is_safe ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  type RowData = Props['ticketDetails']['details']['infos']['MongoReplicaSet' | 'MongoShardedCluster'][number];

  interface Props {
    ticketDetails: TicketModel<Mongodb.ResourcePool.ReduceShardNodes>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_REDUCE_SHARD_NODES,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = computed(() => {
    return [
      ...props.ticketDetails.details.infos.MongoShardedCluster.map((item) => ({
        ...item,
        cluster_ids: [item.cluster_id],
        cluster_type_text: t('分片'),
      })),
      ...props.ticketDetails.details.infos.MongoReplicaSet.map((item) => ({ ...item, cluster_type_text: t('副本集') })),
    ];
  });
</script>
