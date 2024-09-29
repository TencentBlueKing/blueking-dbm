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
        <I18nT keypath="m_耗时_t">
          <span style="color: #ea3636">{{ t('执行失败') }}</span>
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
        <div
          v-if="[0, 2].includes(data.err_code)"
          class="mt-12">
          <DbPopconfirm
            :confirm-handler="handleRetry"
            :content="t('重新执行后无法撤回，请谨慎操作！')"
            :title="t('是否确认重试此步骤')">
            <BkButton
              class="w-88"
              theme="primary">
              {{ t('重试') }}
            </BkButton>
          </DbPopconfirm>
        </div>
      </slot>
      <div
        v-if="data.err_msg"
        style="padding: 12px; margin-top: 12px; background: #f5f7fa; border: 2px">
        {{ data.err_msg }}
      </div>
      <!-- 系统自动终止 -->
      <template v-if="data.err_code === 3 && data.context.expire_time && data.todos.length === 0">
        <div style="margin-top: 8px; color: #ea3636">
          <span>{{ t('system已处理') }}</span>
          <span> ({{ t('超过n天未处理，自动终止', { n: data.context.expire_time }) }}) </span>
        </div>
        <div class="flow-time">
          {{ utcDisplayTime(data.update_at) }}
        </div>
      </template>
    </template>
    <template #desc>
      {{ utcDisplayTime(data.update_at) }}
    </template>
  </DbTimeLineItem>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';
  import TicketModel from '@services/model/ticket/ticket';
  import { retryFlow } from '@services/source/ticketFlow';

  import { useEventBus } from '@hooks';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  import DbTimeLineItem from '../time-line/TimeLineItem.vue';

  interface Props {
    data: FlowMode<unknown, any>;
    ticketDetail: TicketModel<unknown>;
  }

  const props = defineProps<Props>();

  defineSlots<{
    title: () => VNode;
    content: () => VNode;
  }>();

  defineOptions({
    name: FlowMode.STATUS_FAILED,
  });

  const eventBus = useEventBus();
  const { t } = useI18n();

  const handleRetry = () =>
    retryFlow({
      id: props.ticketDetail.id,
      flow_id: props.data.id,
    }).then(() => eventBus.emit('refreshTicketStatus'));
</script>
