<template>
  <ClusterSwitch :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import ClusterSwitch from './common/ClusterSwitch.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ClusterSwitch>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_HA_DESTROY,
    inheritAttrs: false,
  });
</script>
