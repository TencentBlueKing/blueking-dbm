<template>
  <div>
    <div>
      <I18nT
        keypath="n 已处理_c_耗时 t"
        scope="global">
        <span>{{ data.done_by }}</span>
        <span style="color: #2dcb56">{{ t('确认执行') }}</span>
        <CostTimer
          :is-timing="false"
          :start-time="utcTimeToSeconds(data.done_at)"
          :value="data.cost_time" />
      </I18nT>
      <template v-if="flowData.url">
        <span> ，</span>
        <a
          :href="flowData.url"
          target="_blank">
          {{ t('查看详情') }}
        </a>
      </template>
    </div>
    <div style="margin-top: 10px; color: #979ba5">{{ utcDisplayTime(data.done_at) }}</div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  interface Props {
    data: FlowMode<unknown>['todos'][number];
    flowData: FlowMode<unknown>;
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.TODO_STATUS_DONE_SUCCESS,
  });

  const { t } = useI18n();
</script>
