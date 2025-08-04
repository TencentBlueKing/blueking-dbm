<template>
  <DbTimeLineItem>
    <template #icon>
      <div style="width: 10px; height: 10px; background: #ea3636; border-radius: 50%" />
    </template>
    <template #title>
      <slot name="title">
        {{ data.flow_type_display }}
      </slot>
    </template>
    <template #content>
      <slot name="content">
        <I18nT
          keypath="m_处理人_p"
          scope="global">
          <span style="color: #ea3636">{{ t('执行失败') }}</span>
          {{ ticketDetail.todo_operators.join(',') }}
        </I18nT>
        <I18nT
          v-if="ticketDetail.todo_helpers.length > 0"
          keypath="_协助人_p"
          scope="global">
          {{ ticketDetail.todo_helpers.join(',') }}
        </I18nT>
        <I18nT
          keypath="_耗时_t"
          scope="global">
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
      </slot>
      <FlowCollapse
        v-if="data.err_msg"
        danger
        :title="t('失败原因')">
        <div
          class="pl-16"
          :style="{
            'white-space': 'pre-wrap',
            'max-height': `${errMessageMaxHeight}px`,
            overflow: 'auto',
          }">
          {{ data.err_msg }}
        </div>
      </FlowCollapse>
      <div
        v-if="isCanOperation && isNeedOperation"
        class="mt-12">
        <ProcessRetry
          :data="ticketDetail"
          :flow-data="data">
          <BkButton
            class="w-88"
            theme="primary">
            {{ t('失败重试') }}
          </BkButton>
        </ProcessRetry>
      </div>
      <!-- 系统自动终止 -->
      <template v-if="data.err_code === 3 && data.context.expire_time && renderTodoList.length === 0">
        <div style="margin-top: 8px; color: #ea3636">
          <span>{{ t('system已处理') }}</span>
          <span> ({{ t('超过n天未处理，自动终止', { n: data.context.expire_time }) }}) </span>
        </div>
        <div class="flow-time">
          {{ utcDisplayTime(data.update_at) }}
        </div>
      </template>
      <Abstract :data="data" />
    </template>
    <template #desc>
      {{ utcDisplayTime(data.update_at) }}
    </template>
  </DbTimeLineItem>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { type VNode } from 'vue';
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';

  import { useUserProfile } from '@stores';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import ProcessRetry from '@views/ticket-center/common/action-confirm/ProcessRetry.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  import DbTimeLineItem from '../time-line/TimeLineItem.vue';

  import Abstract from './components/abstract/Index.vue';
  import FlowCollapse from './components/FlowCollapse.vue';

  interface Props {
    data: FlowMode<unknown, any>;
    ticketDetail: TicketModel<unknown>;
  }

  defineOptions({
    name: FlowMode.STATUS_FAILED,
  });

  const props = defineProps<Props>();

  defineSlots<{
    content: () => VNode;
    title: () => VNode;
  }>();

  const { t } = useI18n();
  const { isSuperuser, username } = useUserProfile();

  const errMessageMaxHeight = window.innerHeight * 0.4;

  const isCanOperation = computed(
    () =>
      isSuperuser ||
      props.ticketDetail.todo_operators.includes(username) ||
      props.ticketDetail.todo_helpers.includes(username),
  );
  const isNeedOperation = computed(() => [0, 2].includes(props.data.err_code));
  const renderTodoList = computed(() =>
    _.filter(props.data.todos, (item) => item.type !== FlowMode.TODO_TYPE_INNER_FAILED),
  );
</script>
