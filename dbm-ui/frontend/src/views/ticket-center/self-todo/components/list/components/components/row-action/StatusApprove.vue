<template>
  <ProcessPass :data="data">
    <BkButton
      text
      theme="primary">
      {{ t('通过') }}
    </BkButton>
  </ProcessPass>
  <ProcessRefuse :data="data">
    <BkButton
      class="ml-8"
      text
      theme="primary">
      {{ t('拒绝') }}
    </BkButton>
  </ProcessRefuse>
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

  import ProcessPass from '@views/ticket-center/common/action-confirm/ProcessPass.vue';
  import ProcessRefuse from '@views/ticket-center/common/action-confirm/ProcessRefuse.vue';

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
