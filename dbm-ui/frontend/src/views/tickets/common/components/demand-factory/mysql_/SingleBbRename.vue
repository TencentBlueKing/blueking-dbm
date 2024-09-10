<template>
  <DBRename :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import DBRename from './common/DBRename.vue';

  import { TicketTypes } from '@/common/const';

  interface Props {
    ticketDetails: TicketModel<Mysql.DataMigrate>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_SINGLE_DISABLE,
  });
</script>
