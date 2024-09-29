<template>
  <DbTimeLineItem>
    <template #icon>
      <div style="width: 10px; height: 10px; background: #ea3636; border-radius: 50%" />
    </template>
    <template #title>
      <slot name="title"> {{ data.flow_type_display }} </slot>
    </template>
    <template #content>
      <slot name="content">
        <TodoList
          v-if="data.todos.length > 0"
          :data="data.todos"
          :flow-data="data" />
        <div v-else>
          <I18nT
            keypath="m_耗时_t"
            scope="global">
            <span style="color: #ea3636">{{ t('任务终止') }}</span>
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
        </div>
      </slot>
      <div
        v-if="data.err_msg"
        style="padding: 12px; margin-top: 12px; background: #f5f7fa; border: 2px">
        {{ data.err_msg }}
      </div>
    </template>
    <template
      v-if="data.todos.length < 1"
      #desc>
      {{ data.updateAtDisplay }}
    </template>
  </DbTimeLineItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import DbTimeLineItem from '../time-line/TimeLineItem.vue';
  import TodoList from '../todo-list/Index.vue';

  interface Props {
    data: FlowMode<unknown, any>;
  }

  defineProps<Props>();

  defineSlots<{
    title: () => VNode;
    content: () => VNode;
  }>();

  defineOptions({
    name: FlowMode.STATUS_TERMINATED,
  });

  const { t } = useI18n();
</script>
