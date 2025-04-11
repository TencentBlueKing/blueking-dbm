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
        {{ ticketDetails.details.clusters?.[row.cluster_id]?.immute_domain || '--' }}
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
      <template #default>
        {{ specInfo.name }}
        <SpecPanel
          v-if="specInfo.id"
          :data="specInfo"
          :hide-qps="!specInfo.qps.min">
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
        {{ row.old_nodes.mongos?.length > 0 ? row.old_nodes.mongos.map((item) => item.ip).join(',') : '--' }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import SpecPanel, { type SpecInfo } from '@components/render-table/columns/spec-display/Panel.vue';

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

  const specInfo = ref<SpecInfo>({
    cpu: {
      max: 0,
      min: 0,
    },
    id: 0,
    mem: {
      max: 0,
      min: 0,
    },
    name: '--',
    qps: {
      max: 0,
      min: 0,
    },
    storage_spec: [],
  });

  watch(
    () => props.ticketDetails.details,
    () => {
      if (props.ticketDetails.details?.mackine_infos) {
        Object.values(props.ticketDetails.details.mackine_infos).forEach(
          (item: Props['ticketDetails']['details']['mackine_infos'][string]) => {
            if (item.spec_config) {
              specInfo.value = item.spec_config;
            }
          },
        );
      }
    },
    {
      immediate: true,
    },
  );
</script>
<style lang="less" scoped>
  .visible-icon {
    font-size: 16px;
    color: #3a84ff;
    cursor: pointer;
  }
</style>
