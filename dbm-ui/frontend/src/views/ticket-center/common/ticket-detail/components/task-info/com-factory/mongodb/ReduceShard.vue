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
  <!-- 布局与提单页对齐：InfoList 承载表单项（缩容方式），TicketInfoTable 承载表格内容 -->
  <InfoList>
    <InfoItem :label="t('缩容方式')">
      {{ ticketDetails.details.infos[0]?.reduce_mode === 'by_count' ? t('指定数量') : t('指定分片') }}
    </InfoItem>
  </InfoList>
  <TicketInfoTable
    :data="ticketDetails.details.infos"
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="cluster_id"
      :get-copy-value="(row: RowData) => ticketDetails.details.clusters[row.cluster_id]?.immute_domain"
      :min-width="350"
      :title="t('目标集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id]?.immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="current_shard_num"
      :title="t('当前分片数')"
      :width="120">
      <template #default="{ row }: { row: RowData }">
        <span v-if="row.current_shard_num !== undefined">{{ row.current_shard_num }}</span>
        <span v-else>--</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      :col-key="ticketDetails.details.infos[0]?.reduce_mode === 'by_count' ? 'reduce_shards_num' : 'shard_names'"
      :min-width="200"
      :title="ticketDetails.details.infos[0]?.reduce_mode === 'by_count' ? t('缩容分片数') : t('缩容分片')">
      <template #default="{ row }: { row: RowData }">
        <TagBlock
          v-if="row.reduce_mode === 'by_shard_names'"
          :data="row.shard_names || []" />
        <span v-else>{{ row.reduce_shards_num }}</span>
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="final_shard_num"
      :title="t('最终分片数')"
      :width="120">
      <template #default="{ row }: { row: RowData }">
        {{ getFinalShardNum(row) }}
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="tsx">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import TagBlock from '@components/tag-block/Index.vue';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  type RowData = Props['ticketDetails']['details']['infos'][number];

  interface Props {
    ticketDetails: TicketModel<Mongodb.ReduceShard>;
  }

  defineOptions({
    name: TicketTypes.MONGODB_REDUCE_SHARD,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  // 最终分片数前端演算：指定分片 = 当前 − 分片名数；指定数量 = 当前 − 缩容数
  const getFinalShardNum = (row: RowData) => {
    if (row.current_shard_num === undefined) {
      return '--';
    }
    const reduceNum = row.reduce_mode === 'by_count' ? row.reduce_shards_num || 0 : row.shard_names?.length || 0;
    return row.current_shard_num - reduceNum;
  };
</script>
