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
      field="cluster_ids"
      fixed="left"
      :label="t('目标集群')"
      :min-width="250">
      <template #default="{data}: {data: RowData}">
        <div
          v-for="item in data.cluster_ids"
          :key="item">
          {{ ticketDetails.details.clusters[item].immute_domain }}
        </div>
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="cluster_type"
      :label="t('集群类型')"
      :width="200">
      <template #default="{data}: {data: RowData}">
        {{ ticketDetails.details.clusters[data.cluster_ids[0]].cluster_type_name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="current_shard_nodes_num"
      :label="t('当前Shard的节点数')">
    </BkTableColumn>
    <BkTableColumn
      field="add_shard_nodes_num"
      :label="t('扩容至（节点数）')"
      :min-width="120">
      <template #default="{data}: {data: RowData}">
        {{ data.current_shard_nodes_num + data.add_shard_nodes_num }}
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('忽略业务连接')">
      {{ ticketDetails.details.is_safe ? t('否') : t('是') }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  type RowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Mongodb.AddShardNodes>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_ADD_SHARD_NODES,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
