<template>
  <ProcessResourceReplenish :data="data">
    <BkButton
      text
      theme="primary">
      {{ t('重试') }}
    </BkButton>
  </ProcessResourceReplenish>
  <ProcessTerminate :data="data">
    <BkButton
      class="ml-8"
      text
      theme="primary">
      {{ t('终止单据') }}
    </BkButton>
  </ProcessTerminate>
  <TicketDetailLink
    class="ml-8"
    :data="data" />
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import ProcessResourceReplenish from '@views/ticket-center/common/action-confirm/ProcessResourceReplenish.vue';
  import ProcessTerminate from '@views/ticket-center/common/action-confirm/ProcessTerminate.vue';
  import TicketDetailLink from '@views/ticket-center/common/TicketDetailLink.vue';

  interface Props {
    data: TicketModel;
  }

  defineProps<Props>();
  defineOptions({
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
