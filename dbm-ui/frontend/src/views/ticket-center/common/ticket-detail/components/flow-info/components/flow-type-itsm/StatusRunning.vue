<template>
  <StatusRunning :data="data">
    <template #content>
      <I18nT keypath="处理人_p_耗时_t">
        <span>{{ data.summary.operator }}</span>
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
    </template>
  </StatusRunning>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import StatusRunning from '../flow-type-common/StatusRunning.vue';

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
    name: FlowMode.STATUS_RUNNING,
  });

  const { t } = useI18n();
</script>
