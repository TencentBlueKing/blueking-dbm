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
    :data="tableData"
    :merge-cells="mergeCells"
    show-overflow-tooltip>
    <BkTableColumn
      field="instance"
      :label="t('目标实例')"
      :min-width="220">
    </BkTableColumn>
    <BkTableColumn
      :label="t('所属集群')"
      :min-width="130">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn
      :label="t('架构版本')"
      :min-width="130">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].cluster_type_name }}
      </template>
    </BkTableColumn>
  </BkTable>
  <InfoList>
    <InfoItem :label="t('分析时长')">
      {{ `${ticketDetails.details.analysis_time}s` }}
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import type { VxeTablePropTypes } from '@blueking/vxe-table';

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

  const mergeCells = ref<VxeTablePropTypes.MergeCells>([]);

  const tableData = props.ticketDetails.details.infos.flatMap((infoItem) =>
    infoItem.ins.map((insItem) => ({
      cluster_id: infoItem.cluster_id,
      instance: insItem,
    })),
  );
</script>
