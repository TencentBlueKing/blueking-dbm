<template>
  <DbTimeLineItem>
    <template #icon>
      <div style="width: 10px; height: 10px; background: #2dcb56; border-radius: 50%" />
    </template>
    <template #title>
      <slot name="title"> {{ data.flow_type_display }} </slot>
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
            <span style="color: #2dcb56">{{ t('执行成功') }}</span>
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
        </span>
        <div
          v-if="data.summary"
          style="margin-top: 12px; line-height: 16px; color: #63656e">
          <I18nT
            keypath="备注：c"
            scope="global">
            <span>{{ data.summary }}</span>
          </I18nT>
        </div>
      </slot>
      <slot name="contentPreppend" />
      <FlowCollapse
        v-if="data.err_msg"
        danger
        :title="t('失败原因')">
        <div style="padding-left: 16px">
          {{ data.err_msg }}
        </div>
      </FlowCollapse>
      <Abstract :data="data" />
    </template>
    <template
      v-if="renderTodoList.length < 1"
      #desc>
      {{ data.updateAtDisplay }}
    </template>
  </DbTimeLineItem>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { type VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import DbTimeLineItem from '../time-line/TimeLineItem.vue';
  import TodoList from '../todo-list/Index.vue';

  import Abstract from './components/abstract/Index.vue';
  import FlowCollapse from './components/FlowCollapse.vue';

  interface Props {
    data: FlowMode<unknown, any>;
  }

  defineOptions({
    name: FlowMode.STATUS_SKIPPED,
  });

  const props = defineProps<Props>();

  defineSlots<{
    content: () => VNode;
    contentPreppend: () => VNode;
    title: () => VNode;
  }>();

  const { t } = useI18n();

  const renderTodoList = computed(() =>
    _.filter(props.data.todos, (item) => item.type !== FlowMode.TODO_TYPE_INNER_FAILED),
  );
</script>
