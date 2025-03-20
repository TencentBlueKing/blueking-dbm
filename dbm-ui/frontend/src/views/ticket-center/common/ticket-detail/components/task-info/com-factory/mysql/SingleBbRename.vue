<template>
  <DBRename :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@/common/const';

  import DBRename from './common/DBRename.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.HaRenameDatabase>;
  }

  defineOptions({
    name: TicketTypes.MYSQL_SINGLE_RENAME_DATABASE,
    inheritAttrs: false,
  });

  defineProps<Props>();
</script>
