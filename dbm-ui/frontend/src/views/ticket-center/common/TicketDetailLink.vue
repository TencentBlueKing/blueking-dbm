<template>
  <RouterLink
    target="_blank"
    :to="{
      name: 'ticketDetail',
      params: {
        ticketId: data.id,
      },
    }">
    {{ t('新窗口打开') }}
  </RouterLink>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  interface Props {
    data: TicketModel;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
