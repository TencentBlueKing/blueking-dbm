<template>
  <StatusSucceeded
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
        <span style="color: #2dcb56">{{ t('已通过') }}</span>
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
      <TodoList
        v-if="data.todos.length > 0"
        :data="data.todos"
        :flow-data="data"
        :modify-records="modifyRecords" />
    </template>
  </StatusSucceeded>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import type TicketModifyRecordModel from '@services/model/ticket/modify-record';
  import TicketModel from '@services/model/ticket/ticket';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import ProcessedLine from '../components/ProcessedLine.vue';
  import StatusSucceeded from '../flow-type-common/StatusSucceeded.vue';
  import TodoList from '../todo-list/Index.vue';

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
    ticketDetail: TicketModel<any>;
  }

  defineOptions({
    name: FlowMode.STATUS_SUCCEEDED,
  });

  const props = defineProps<Props>();

  const { t } = useI18n();
  const { itsmOperators, onBehalfRecord } = useOnBehalfExit(
    () => props.data,
    () => props.modifyRecords,
  );
</script>
