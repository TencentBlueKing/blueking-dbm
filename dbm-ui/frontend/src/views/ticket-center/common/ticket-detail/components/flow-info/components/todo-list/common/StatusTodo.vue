<template>
  <div>
    <div>
      <I18nT
        keypath="处理人_p_耗时_t"
        scope="global">
        <span>{{ data.operators.join(',') }}</span>
        <CostTimer
          is-timing
          :start-time="utcTimeToSeconds(flowData.start_time)"
          :value="flowData.cost_time" />
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
    <template v-if="isSuperuser || data.operators.includes(username)">
      <ProcessApproveExce :todo-data="data">
        <BkButton
          class="w-88"
          theme="primary">
          {{ t('确认执行') }}
        </BkButton>
      </ProcessApproveExce>
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

  import ProcessApproveExce from '@views/ticket-center/common/action-confirm/ProcessApproveExce.vue';
  import ProcessTerminate from '@views/ticket-center/common/action-confirm/ProcessTerminate.vue';

  import { utcDisplayTime, utcTimeToSeconds } from '@utils';

  interface Props {
    data: FlowMode<unknown>['todos'][number];
    flowData: FlowMode<unknown>;
  }

  defineProps<Props>();

  defineOptions({
    name: FlowMode.TODO_STATUS_TODO,
  });

  const { t } = useI18n();
  const { username, isSuperuser } = useUserProfile();
</script>
