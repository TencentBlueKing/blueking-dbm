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
    :data="tableData"
    row-key="cluster_id">
    <TicketInfoTableColumn
      col-key="addr"
      fixed="left"
      :get-copy-value="(row: RowData) => row.instance.addr"
      :min-width="220"
      :title="t('目标实例')">
      <template #default="{ row }: { row: RowData }">
        {{ row.instance.addr }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="immute_domain"
      :min-width="300"
      :title="t('所属集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_type_name"
      :title="t('架构版本')"
      :width="150">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].cluster_type_name }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="memory_total"
      :title="t('内存大小')"
      :width="150">
      <template #default="{ row }: { row: RowData }">
        {{ bytePretty(row.instance.memory_total) }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="ikey_num"
      :title="t('Key 数量')"
      :width="150">
      <template #default="{ row }: { row: RowData }">
        {{ row.instance.key_num }}
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import { bytePretty } from '@utils';

  type RowData = (typeof tableData)[number];

  interface Props {
    ticketDetails: TicketModel<Redis.KeyStat>;
  }

  defineOptions({
    name: TicketTypes.REDIS_KEYSTAT,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  const tableData = props.ticketDetails.details.infos.flatMap((infoItem) =>
    infoItem.ins.map((insItem) => ({
      cluster_id: infoItem.cluster_id,
      instance: insItem,
    })),
  );
</script>
