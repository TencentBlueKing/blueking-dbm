<template>
  <ProcessApproveExce :data="data">
    <BkButton
      text
      theme="primary">
      {{ t('确认执行') }}
    </BkButton>
  </ProcessApproveExce>
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

  import ProcessApproveExce from '@views/ticket-center/common/action-confirm/ProcessApproveExce.vue';
  import ProcessTerminate from '@views/ticket-center/common/action-confirm/ProcessTerminate.vue';

  interface Props {
    data: TicketModel;
  }

  defineOptions({
    inheritAttrs: false,
  });
  defineProps<Props>();
  const { t } = useI18n();
</script>
