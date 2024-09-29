<template>
  <div>
    <I18nT
      keypath="处理人_p_耗时_t"
      scope="global">
      <span>{{ data.operators.join(',') }}</span>
      <CostTimer
        :is-timing="false"
        :start-time="utcTimeToSeconds(flowData.start_time)"
        :value="data.cost_time" />
    </I18nT>
    <div style="margin-top: 10px; color: #979ba5">{{ utcDisplayTime(data.done_at) }}</div>
    <template v-if="isSuperuser || data.operators.includes(username)">
      <ProcessResourceReplenish :todo-data="data">
        <BkButton
          class="w-88"
          theme="primary">
          {{ t('重试') }}
        </BkButton>
      </ProcessResourceReplenish>
      <ProcessTerminate :todo-data="data">
        <BkButton
          class="w-88 ml-8"
          theme="danger">
          {{ t('终止单据') }}
        </BkButton>
      </ProcessTerminate>
    </template>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import FlowMode from '@services/model/ticket/flow';

  import { useUserProfile } from '@stores';

  import CostTimer from '@components/cost-timer/CostTimer.vue';

  import ProcessResourceReplenish from '@views/ticket-center/common/action-confirm/ProcessResourceReplenish.vue';
  import ProcessTerminate from '@views/ticket-center/common/action-confirm/ProcessTerminate.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  interface Props {
    data: FlowMode<unknown>['todos'][number];
    flowData: FlowMode<unknown>;
  }

  defineProps<Props>();

  const { t } = useI18n();
  const { username, isSuperuser } = useUserProfile();
</script>
