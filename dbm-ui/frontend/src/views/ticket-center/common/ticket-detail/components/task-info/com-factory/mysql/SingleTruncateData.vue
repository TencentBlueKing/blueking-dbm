<template>
  <TruncateData :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@/common/const';

  import TruncateData from '../common/mysql-truncate-data/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.TruncateData>;
  }

  defineOptions({
    name: TicketTypes.MYSQL_SINGLE_TRUNCATE_DATA,
    inheritAttrs: false,
  });

  defineProps<Props>();
</script>
