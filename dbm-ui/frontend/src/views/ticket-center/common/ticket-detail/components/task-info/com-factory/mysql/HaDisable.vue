<template>
  <BatchClusterOperation :ticket-details="ticketDetails" />
</template>

<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import BatchClusterOperation from '../common/BatchClusterOperation.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.HaDisable>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_HA_DISABLE,
    inheritAttrs: false,
  });
</script>
