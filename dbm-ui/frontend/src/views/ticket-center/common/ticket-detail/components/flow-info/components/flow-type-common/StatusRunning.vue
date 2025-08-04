<template>
  <DbTimeLineItem>
    <template #icon>
      <DbIcon
        class="rotate-loading"
        style="font-size: 14px; color: #3a84ff"
        svg
        type="loading-tubiao" />
    </template>
    <template #title>
      <slot name="title">
        {{ data.flow_type_display }}
      </slot>
    </template>
    <template #content>
      <slot name="content">
        <TodoList
          v-if="renderTodoList.length > 0"
          :data="renderTodoList"
          :flow-data="data" />
        <span v-else>
          <I18nT
            keypath="m_耗时_t"
            scope="global">
            <span style="color: #3a84ff">{{ t('执行中') }}</span>
            <CostTimer
              is-timing
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
        </span>
      </slot>
      <Abstract :data="data" />
    </template>
  </DbTimeLineItem>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import type { VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import DbTimeLineItem from '../time-line/TimeLineItem.vue';
  import TodoList from '../todo-list/Index.vue';

  import Abstract from './components/abstract/Index.vue';

  interface Props {
    data: FlowMode<unknown, any>;
  }

  defineOptions({
    name: FlowMode.STATUS_RUNNING,
  });

  const props = defineProps<Props>();

  defineSlots<{
    content: () => VNode;
    title: () => VNode;
  }>();

  const { t } = useI18n();

  const renderTodoList = computed(() =>
    _.filter(props.data.todos, (item) => item.type !== FlowMode.TODO_TYPE_INNER_FAILED),
  );
</script>
