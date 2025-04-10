<template>
  <StatusSucceeded :data="data">
    <template #title>
      {{ data.flow_type_display }}
    </template>
    <template #content>
      <TodoList
        v-if="data.todos.length > 0"
        :data="data.todos"
        :flow-data="data" />
      <span v-else>
        <I18nT
          keypath="m_耗时_t"
          scope="global">
          <span style="color: #2dcb56">{{ t('执行成功') }}</span>
          <CostTimer
            :is-timing="false"
            :start-time="utcTimeToSeconds(data.start_time)"
            :value="data.cost_time" />
        </I18nT>
        <span>，</span>
        <BkButton
          text
          theme="primary"
          @click="handleToggleResourceDetail">
          {{ t('资源明细') }}
          <DbIcon
            class="ml-4"
            type="down-big" />
        </BkButton>
      </span>
      <ResourceDetail
        v-if="isShowResourceDetail"
        class="mt-16"
        :ticket-detail="ticketDetail" />
    </template>
  </StatusSucceeded>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import StatusSucceeded from '../flow-type-common/StatusSucceeded.vue';
  import TodoList from '../todo-list/Index.vue';

  import ResourceDetail from './components/ResourceDetail.vue';

  interface Props {
    data: FlowMode;
    ticketDetail: TicketModel<any>;
  }

  defineOptions({
    name: FlowMode.STATUS_SUCCEEDED,
  });

  defineProps<Props>();

  const { t } = useI18n();

  const isShowResourceDetail = ref(false);

  const handleToggleResourceDetail = () => {
    isShowResourceDetail.value = !isShowResourceDetail.value;
  };
</script>
