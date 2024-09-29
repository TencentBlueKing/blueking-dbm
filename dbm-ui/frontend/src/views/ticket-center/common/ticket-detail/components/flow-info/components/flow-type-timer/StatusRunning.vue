<template>
  <DbTimeLineItem>
    <template #icon>
      <DbIcon
        style="font-size: 14px; color: #3a84ff"
        svg
        type="timed-task" />
    </template>
    <template #title>
      <slot name="title">
        {{ data.flow_type_display }}
      </slot>
    </template>
    <template #content>
      <I18nT
        keypath="定时时间_m_倒计时_t"
        scope="global">
        <span>{{ utcDisplayTime(data.details.run_time) }}</span>
        <RunCountdown :model-value="data.details.run_time" />
      </I18nT>
    </template>
  </DbTimeLineItem>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';

  import { utcDisplayTime } from '@utils';

  import DbTimeLineItem from '../time-line/TimeLineItem.vue';

  import RunCountdown from './components/RunCountdown.vue';

  interface Props {
    data: FlowMode<{
      run_time: string;
    }>;
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.STATUS_RUNNING,
  });
</script>
