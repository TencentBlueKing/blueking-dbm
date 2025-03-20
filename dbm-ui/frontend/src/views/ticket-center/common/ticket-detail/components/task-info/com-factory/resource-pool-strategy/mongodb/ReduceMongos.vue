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
      fixed="left"
      :label="t('目标分片集群')"
      :min-width="200">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('缩容节点类型')"
      :min-width="150">
      <template #default> mongos </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('当前规格')"
      :min-width="150">
      <template #default="{ row }: { row: RowData }">
        {{ specMap[row.cluster_id]?.spec_name || '--' }}
        <SpecPanel
          v-if="specMap[row.cluster_id]?.spec_id"
          :data="specMap[row.cluster_id]"
          :hide-qps="!specMap[row.cluster_id]?.qps?.min">
          <DbIcon
            class="visible-icon ml-4"
            type="visible1" />
        </SpecPanel>
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('缩容的IP')"
      :min-width="150">
      <template #default="{ row }: { row: RowData }">
        {{ row.old_nodes.mongos.map((item) => item.ip).join(',') }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import MongoDBModel from '@services/model/mongodb/mongodb';
  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';
  import { filterClusters } from '@services/source/dbbase';

  import { TicketTypes } from '@common/const';

  import SpecPanel from '@components/render-table/columns/spec-display/Panel.vue';

  interface Props {
    ticketDetails: TicketModel<Mongodb.ResourcePool.ReduceMongos>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][0];

  defineOptions({
    name: TicketTypes.MONGODB_REDUCE_MONGOS,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const specMap = reactive<Record<string, MongoDBModel['cluster_spec']>>({});

  useRequest(filterClusters<MongoDBModel>, {
    defaultParams: [
      {
        bk_biz_id: props.ticketDetails.bk_biz_id,
        cluster_ids: Object.keys(props.ticketDetails.details.clusters).join(','),
      },
    ],
    onSuccess: (data) => {
      data.forEach((item) => {
        Object.assign(specMap, {
          [item.id]: item.cluster_spec,
        });
      });
    },
  });
</script>
<style lang="less" scoped>
  .visible-icon {
    font-size: 16px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
