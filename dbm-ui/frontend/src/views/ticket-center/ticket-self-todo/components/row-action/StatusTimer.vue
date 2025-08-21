<template>
  <ProcessTimerExce
    :data="data"
    :placeholder="t('确定后，单据将跳过定时步骤立即进入下一步骤')">
    <BkButton
      text
      theme="primary">
      {{ t('立即执行') }}
    </BkButton>
  </ProcessTimerExce>
  <ProcessTerminate :data="data">
    <BkButton
      class="ml-8"
      text
      theme="primary">
      {{ t('终止单据') }}
    </BkButton>
  </ProcessTerminate>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import ProcessTerminate from '@views/ticket-center/common/action-confirm/ProcessTerminate.vue';
  import ProcessTimerExce from '@views/ticket-center/common/action-confirm/ProcessTimerExce.vue';

  interface Props {
    data: TicketModel;
  }

  defineOptions({
    inheritAttrs: false,
  });
  defineProps<Props>();
  const { t } = useI18n();
</script>
