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
  <BkTable
    :data="ticketDetails.details.infos"
    :merge-cells="mergeCells">
    <BkTableColumn
      field="display_info.instance"
      :label="t('目标 Master 实例')">
    </BkTableColumn>
    <BkTableColumn
      field="cluster_id"
      :label="t('所属集群')"
      :rowspan="3">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="resource_spec"
      :label="t('规格')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.specs[data.resource_spec.backend_group.spec_id].name }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      field="display_info.db_version"
      :label="t('版本')">
      <template #default="{ data }: { data: RowData }">
        <div
          v-for="version in data.display_info.db_version"
          :key="version"
          style="line-height: 20px">
          {{ version }}
        </div>
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import type { UnwrapRef } from 'vue';
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import type { VxeTablePropTypes } from '@blueking/vxe-table';

  interface Props {
    ticketDetails: TicketModel<Redis.MigrateCluster>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  const props = defineProps<Props>();

  defineOptions({
    name: TicketTypes.REDIS_CLUSTER_INS_MIGRATE,
    inheritAttrs: false,
  });

  const { t } = useI18n();

  const mergeCells = ref<VxeTablePropTypes.MergeCells>([]);

  watchEffect(() => {
    const { infos, clusters } = props.ticketDetails.details;
    const domainMap = infos.reduce<Record<string, number>>((prevMap, infoItem) => {
      const domain = clusters[infoItem.cluster_id].immute_domain;
      if (prevMap[domain]) {
        return Object.assign({}, prevMap, { [domain]: prevMap[domain] + 1 });
      }
      return Object.assign({}, prevMap, { [domain]: 1 });
    }, {});
    mergeCells.value = Object.values(domainMap).reduce<UnwrapRef<typeof mergeCells>>((prevMergeCells, count) => {
      const row = prevMergeCells.length ? prevMergeCells[prevMergeCells.length - 1].rowspan : 0;
      const item = { row, col: 1, rowspan: count, colspan: 1 };
      return prevMergeCells.concat(item);
    }, []);
  });
</script>
