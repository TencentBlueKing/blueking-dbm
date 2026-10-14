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

<template>
  <div>
    <ProcessedLine
      :cost-time="data.cost_time"
      :exit-color="reEditRecord ? '#63656e' : '#2dcb56'"
      :exit-text="reEditRecord ? t('重新提交') : t('确认无误')"
      :operator="reEditRecord?.operator || data.done_by"
      :operators="data.operators"
      :start-time="utcTimeToSeconds(data.done_at)" />
    <SummaryModifyRecord
      v-if="summaryRecord"
      :record="summaryRecord"
      :ticket-detail="ticketData" />
    <div
      class="mt-12"
      style="color: #979ba5">
      {{ utcDisplayTime(data.done_at) }}
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  import ProcessedLine from '../../components/ProcessedLine.vue';
  import SummaryModifyRecord from '../../components/SummaryModifyRecord.vue';
  import { getSummaryRecord } from '../../components/summaryRecord';

  interface Props {
    data: FlowMode<unknown>['todos'][number];
    flowData: FlowMode<unknown>;
    modifyRecords: TicketModifyRecordModel[];
    ticketData: TicketModel;
  }

  defineOptions({
    name: FlowMode.TODO_STATUS_DONE_SUCCESS,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();

  // 确认步骤内提交了重新编辑即以「重新提交」结束，否则为直接确认（确认无误）
  const reEditRecord = computed(() =>
    props.modifyRecords.find(
      (item) => item.flow_id === props.flowData.id && item.mode === TicketModifyRecordModel.MODE_RE_EDIT,
    ),
  );

  // 只有这一次重新提交时，变更对比挂在主摘要上，记录块不再展示
  const summaryRecord = computed(() => getSummaryRecord(props.flowData, props.modifyRecords));
</script>
