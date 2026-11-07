<template>
  <StatusTerminated
    :data="data"
    :modify-records="modifyRecords"
    :ticket-detail="ticketDetail">
    <template #content>
      <ProcessedLine
        v-if="onBehalfRecord"
        :cost-time="data.cost_time"
        exit-color="#ff9c01"
        :exit-text="t('代为修改')"
        :operator="onBehalfRecord.operator"
        :operators="itsmOperators"
        :start-time="utcTimeToSeconds(data.start_time)" />
      <I18nT
        v-else
        keypath="n 已处理_c_耗时 t"
        scope="global">
        <bk-user-display-name :user-id="data.summary.operator" />
        <span style="color: #ea3636">{{ statusText }}</span>
        <CostTimer
          :is-timing="false"
          :start-time="utcTimeToSeconds(data.start_time)"
          :value="data.cost_time" />
      </I18nT>
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
      <!-- 主摘要是最后一次处理的结论，带上处理时间；没有待办时通用外壳已在 desc 展示，这里不重复 -->
      <div
        v-if="data.todos.length > 0"
        class="mt-12"
        style="color: #979ba5">
        {{ data.updateAtDisplay }}
      </div>
    </template>
  </StatusTerminated>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import type TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import ProcessedLine from '../components/ProcessedLine.vue';
  import SummaryModifyRecord from '../components/SummaryModifyRecord.vue';
  import { getSummaryRecord } from '../components/summaryRecord';
  import StatusTerminated from '../flow-type-common/StatusTerminated.vue';

  import useOnBehalfExit from './hooks/useOnBehalfExit';

  interface Props {
    data: FlowMode<
      unknown,
      {
        approve_result: boolean;
        message: string;
        operator: string;
        status: string;
      }
    >;
    modifyRecords: TicketModifyRecordModel[];
    ticketDetail: TicketModel<unknown>;
  }

  defineOptions({
    name: FlowMode.STATUS_TERMINATED,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { itsmOperators, onBehalfRecord } = useOnBehalfExit(
    () => props.data,
    () => props.modifyRecords,
  );

  const summaryRecord = computed(() => getSummaryRecord(props.data, props.modifyRecords));

  const statusText = computed(() => {
    if (props.data.summary.status === 'REVOKED') {
      return t('已撤销');
    }
    if (props.data.summary.status === 'FINISHED') {
      return t('已拒绝');
    }

    return t('已关单');
  });
</script>
