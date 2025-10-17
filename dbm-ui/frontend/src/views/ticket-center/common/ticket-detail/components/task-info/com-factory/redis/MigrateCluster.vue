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
    ellipsis>
    <TableColumn
      col-key="migrate_instance"
      :min-width="200"
      :title="t('目标 Master 实例')">
      <template #default="{ row }: { row: RowData }">
        <div
          v-for="(item, index) in (row.display_info?.instance || row.migrate_instance).split(',')"
          :key="index">
          {{ item }}
        </div>
      </template>
    </TableColumn>
    <TableColumn
      col-key="cluster_id"
      :min-width="300"
      :rowspan="3"
      :title="t('所属集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TableColumn>
    <TableColumn
      col-key="resource_spec"
      :title="t('规格')"
      :width="200">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.specs[row.resource_spec.backend_group.spec_id].name }}
      </template>
    </TableColumn>
    <!-- <TableColumn
      col-key="data.db_version"
      :title="t('版本')">
      <template #default="{ row }: { row : RowData }">
        <div
          v-for="version in data.display_info?.db_version || data.db_version"
          :key="version"
          style="line-height: 20px">
          {{ version }}
        </div>
      </template>
    </TableColumn> -->
  </PrimaryTable>
</template>
<script setup lang="ts">
  // import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  // import type { VxeTablePropTypes } from '@blueking/vxe-table';
  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  interface Props {
    ticketDetails: TicketModel<Redis.MigrateCluster>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_INS_MIGRATE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();

  // const mergeCells = ref<VxeTablePropTypes.MergeCells>([]);

  // const { clusters, infos } = props.ticketDetails.details;
  // const domainMap = infos.reduce<Record<string, number>>((prevMap, infoItem) => {
  //   const domain = clusters[infoItem.cluster_id].immute_domain;
  //   if (prevMap[domain]) {
  //     return Object.assign({}, prevMap, { [domain]: prevMap[domain] + 1 });
  //   }
  //   return Object.assign({}, prevMap, { [domain]: 1 });
  // }, {});
  // mergeCells.value = Object.values(domainMap).reduce<UnwrapRef<typeof mergeCells>>((prevMergeCells, count) => {
  //   const row = prevMergeCells.length ? prevMergeCells[prevMergeCells.length - 1].rowspan : 0;
  //   const item = { col: 1, colspan: 1, row, rowspan: count };
  //   return prevMergeCells.concat(item);
  // }, []);
</script>
