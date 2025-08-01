<template>
  <DbTimeLineItem>
    <template #icon>
      <div style="width: 10px; height: 10px; background: #ea3636; border-radius: 50%" />
    </template>
    <template #title>
      <slot name="title"> {{ data.flow_type_display }} </slot>
    </template>
    <template #content>
      <!-- 如果有 err_code 为 3 忽略 flow 和 todo 的信息 -->
      <slot
        v-if="data.err_code !== 3"
        name="content">
        <TodoList
          v-if="renderTodoList.length > 0"
          :data="renderTodoList"
          :flow-data="data" />
        <div v-else>
          <I18nT
            keypath="m_处理人_p_耗时_t"
            scope="global">
            <span style="color: #ea3636">{{ t('任务终止') }}</span>
            <span>{{ ticketDetail.updater }}</span>
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
      <!-- 系统自动终止 -->
      <template v-if="data.err_code === 3">
        <div class="mt-8">
          <span style="color: #ea3636">
            {{ t('系统自动终止（超过 n 天未处理）', { n: data.context.expire_time }) }}
          </span>
          <template v-if="data.url">
            <span> ，</span>
            <a
              :href="data.url"
              target="_blank">
              {{ t('查看详情') }}
            </a>
          </template>
        </div>
      </template>
      <div
        v-if="data.context.remark"
        style="margin-top: 12px; line-height: 16px; color: #63656e">
        <I18nT
          keypath="备注：c"
          scope="global">
          <span>{{ data.context.remark }}</span>
        </I18nT>
      </div>
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
      v-if="data.err_code === 3 || renderTodoList.length < 1"
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
  import TicketModel from '@services/model/ticket/ticket';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import DbTimeLineItem from '../time-line/TimeLineItem.vue';
  import TodoList from '../todo-list/Index.vue';

  import Abstract from './components/abstract/Index.vue';
  import FlowCollapse from './components/FlowCollapse.vue';

  interface Props {
    data: FlowMode<unknown, any>;
    ticketDetail: TicketModel<unknown>;
  }

  defineOptions({
    name: FlowMode.STATUS_TERMINATED,
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
