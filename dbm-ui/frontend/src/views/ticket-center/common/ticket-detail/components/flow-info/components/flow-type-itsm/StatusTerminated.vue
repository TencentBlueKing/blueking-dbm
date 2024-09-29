<template>
  <StatusTerminated :data="data">
    <template #content>
      <I18nT
        keypath="n 已处理_c_耗时 t"
        scope="global">
        <span>{{ data.summary.operator }}</span>
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
      <TodoList
        v-if="data.todos.length > 0"
        :data="data.todos"
        :flow-data="data" />
    </template>
  </StatusTerminated>
</template>
<script setup lang="ts">
  import { computed } from 'vue';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import StatusTerminated from '../flow-type-common/StatusTerminated.vue';
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

  const props = defineProps<Props>();

  defineOptions({
    name: FlowMode.STATUS_TERMINATED,
  });

  const { t } = useI18n();

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
