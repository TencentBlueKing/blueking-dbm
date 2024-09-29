<template>
  <DBRename :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import DBRename from './common/DBRename.vue';

  import { TicketTypes } from '@/common/const';

  interface Props {
    ticketDetails: TicketModel<Mysql.HaRenameDatabase>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.MYSQL_SINGLE_RENAME_DATABASE,
    inheritAttrs: false,
  });
</script>
