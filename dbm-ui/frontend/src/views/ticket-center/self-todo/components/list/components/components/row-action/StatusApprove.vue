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
  <TicketDetailLink
    class="ml-8"
    :data="data" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import ProcessPass from '@views/ticket-center/common/action-confirm/ProcessPass.vue';
  import ProcessRefuse from '@views/ticket-center/common/action-confirm/ProcessRefuse.vue';
  import TicketDetailLink from '@views/ticket-center/common/TicketDetailLink.vue';

  interface Props {
    data: TicketModel<unknown>;
  }

  defineProps<Props>();

  defineOptions({
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
