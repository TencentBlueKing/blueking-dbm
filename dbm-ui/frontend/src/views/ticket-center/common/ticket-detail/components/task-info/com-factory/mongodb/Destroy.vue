<template>
  <Operation :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mongodb } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import Operation from './common/Destroy&Disable&Enable.vue';

  interface Props {
    ticketDetails: TicketModel<Mongodb.Destroy>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MONGODB_DESTROY,
    inheritAttrs: false,
  });
</script>
