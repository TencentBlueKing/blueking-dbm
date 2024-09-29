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
  <BkButton
    class="ml-8"
    text
    theme="primary"
    @click="handleGoDetail">
    {{ t('查看详情') }}
  </BkButton>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import ProcessApproveExce from '@views/ticket-center/common/action-confirm/ProcessApproveExce.vue';
  import ProcessTerminate from '@views/ticket-center/common/action-confirm/ProcessTerminate.vue';

  interface Props {
    data: TicketModel<unknown>;
  }

  interface Emits {
    (e: 'go-ticket-detail', params: TicketModel): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const handleGoDetail = () => {
    emits('go-ticket-detail', props.data);
  };
</script>
