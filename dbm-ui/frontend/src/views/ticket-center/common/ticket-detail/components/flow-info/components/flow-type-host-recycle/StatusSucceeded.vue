<template>
  <StatusSucceeded :data="data">
    <template #content>
      <I18nT
        keypath="m_耗时_t"
        scope="global">
        <span style="color: #2dcb56">
          {{ t('执行成功') }}
          <span v-if="data.summary.status === 'FAILED'">({{ data.summary.message }})</span>
        </span>
        <CostTimer
          :is-timing="false"
          :start-time="utcTimeToSeconds(data.start_time)"
          :value="data.cost_time" />
      </I18nT>
    </template>
  </StatusSucceeded>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import { utcTimeToSeconds } from '@utils';

  import StatusSucceeded from '../flow-type-common/StatusSucceeded.vue';

  interface Props {
    data: FlowMode<
      unknown,
      {
        message: string;
        status: string;
      }
    >;
  }

  defineOptions({
    name: FlowMode.STATUS_SUCCEEDED,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
