<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<!-- 代为修改结束「单据审批」时后端把步骤置为跳过，标题下展示改单出口，不展示「已跳过」备注；其余跳过沿用通用展示 -->
<template>
  <StatusSkipped
    :data="data"
    :modify-records="modifyRecords"
    :ticket-detail="ticketDetail">
    <template
      v-if="onBehalfRecord"
      #content>
      <ProcessedLine
        :cost-time="data.cost_time"
        exit-color="#ff9c01"
        :exit-text="t('代为修改')"
        :operator="onBehalfRecord.operator"
        :operators="itsmOperators"
        :start-time="utcTimeToSeconds(data.start_time)" />
      <template v-if="data.url">
        <span> ，</span>
        <a
          :href="data.url"
          target="_blank">
          {{ t('查看详情') }}
        </a>
      </template>
      <SummaryModifyRecord
        v-if="summaryRecord"
        :record="summaryRecord"
        :ticket-detail="ticketDetail" />
      <TodoList
        v-if="data.todos.length > 0"
        :data="data.todos"
        :flow-data="data"
        :modify-records="modifyRecords" />
    </template>
  </StatusSkipped>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import type TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';

  import { utcTimeToSeconds } from '@utils';

  import ProcessedLine from '../components/ProcessedLine.vue';
  import SummaryModifyRecord from '../components/SummaryModifyRecord.vue';
  import { getSummaryRecord } from '../components/summaryRecord';
  import StatusSkipped from '../flow-type-common/StatusSkipped.vue';
  import TodoList from '../todo-list/Index.vue';

  import useOnBehalfExit from './hooks/useOnBehalfExit';

  interface Props {
    data: FlowMode<unknown, any>;
    modifyRecords: TicketModifyRecordModel[];
    ticketDetail: TicketModel<unknown>;
  }

  defineOptions({
    name: FlowMode.STATUS_SKIPPED,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { itsmOperators, onBehalfRecord } = useOnBehalfExit(
    () => props.data,
    () => props.modifyRecords,
  );

  const summaryRecord = computed(() => getSummaryRecord(props.data, props.modifyRecords));
</script>
