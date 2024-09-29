<template>
  <StatusSucceeded :data="data">
    <template #content>
      <I18nT
        keypath="n 已处理_c_耗时 t"
        scope="global">
        <span>{{ data.summary.operator }}</span>
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
        :flow-data="data" />
    </template>
  </StatusSucceeded>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import StatusSucceeded from '../flow-type-common/StatusSucceeded.vue';
  import TodoList from '../todo-list/Index.vue';

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
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.STATUS_SUCCEEDED,
  });

  const { t } = useI18n();
</script>
