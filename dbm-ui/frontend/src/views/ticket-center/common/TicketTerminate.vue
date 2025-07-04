<template>
  <ProcessFailedTerminate :data="data">
    <BkButton theme="danger">
      {{ t('终止单据') }}
    </BkButton>
  </ProcessFailedTerminate>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import { useUserProfile } from '@stores';

  import ProcessFailedTerminate from '@views/ticket-center/common/action-confirm/ProcessFailedTerminate.vue';

  interface Props {
    data: TicketModel;
  }

  const props = defineProps<Props>();

  const { username } = useUserProfile();
  const { t } = useI18n();

  console.log(props, username);
</script>
