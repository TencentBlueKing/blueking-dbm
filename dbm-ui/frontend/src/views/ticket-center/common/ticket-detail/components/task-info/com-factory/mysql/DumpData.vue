<template>
  <DumpData :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import DumpData from '../common/mysql-dump-data/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.DumpData>;
  }

  defineOptions({
    name: TicketTypes.MYSQL_DUMP_DATA,
    inheritAttrs: false,
  });

  defineProps<Props>();
</script>
