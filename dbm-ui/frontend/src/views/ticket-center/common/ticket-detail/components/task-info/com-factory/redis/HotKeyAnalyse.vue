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
    row-key="instance">
    <TicketInfoTableColumn
      col-key="instance"
      :get-copy-value="(row: RowData) => row.instance"
      :min-width="220"
      :title="t('目标实例')">
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="immute_domain"
      :min-width="130"
      :title="t('所属集群')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].immute_domain }}
      </template>
    </TicketInfoTableColumn>
    <TicketInfoTableColumn
      col-key="cluster_type_name"
      :min-width="130"
      :title="t('架构版本')">
      <template #default="{ row }: { row: RowData }">
        {{ ticketDetails.details.clusters[row.cluster_id].cluster_type_name }}
      </template>
    </TicketInfoTableColumn>
  </TicketInfoTable>
  <InfoList>
    <InfoItem :label="t('分析时长')">
      {{ `${ticketDetails.details.analysis_time}s` }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  // import type { TableProps } from '@blueking/tdesign-ui';
  import TicketModel, { type Redis } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  type RowData = (typeof tableData)[number];

  interface Props {
    ticketDetails: TicketModel<Redis.HotKeyAnalyse>;
  }

  defineOptions({
    name: TicketTypes.REDIS_HOT_KEY_ANALYSIS,
    inheritAttrs: false,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  // const rowspanAndColspan: TableProps['rowspanAndColspan'] = () => {};

  const tableData = props.ticketDetails.details.infos.flatMap((infoItem) =>
    infoItem.ins.map((insItem) => ({
      cluster_id: infoItem.cluster_id,
      instance: insItem,
    })),
  );
</script>
