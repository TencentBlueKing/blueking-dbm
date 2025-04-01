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
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import ProcessPass from '@views/ticket-center/common/action-confirm/ProcessPass.vue';
  import ProcessRefuse from '@views/ticket-center/common/action-confirm/ProcessRefuse.vue';

  interface Props {
    data: TicketModel<unknown>;
  }

  defineOptions({
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
