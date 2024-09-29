<template>
  <TruncateData :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import TruncateData from '../common/mysql-truncate-data/Index.vue';

  import { TicketTypes } from '@/common/const';

  interface Props {
    ticketDetails: TicketModel<Mysql.TruncateData>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_HA_TRUNCATE_DATA,
    inheritAttrs: false,
  });
</script>
