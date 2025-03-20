<template>
  <ImportSqlfile :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import ImportSqlfile from '../common/mysql-import-sqlfile/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.ImportSqlFile>;
  }

  defineOptions({
    name: TicketTypes.MYSQL_FORCE_IMPORT_SQLFILE,
    inheritAttrs: false,
  });

  defineProps<Props>();
</script>
