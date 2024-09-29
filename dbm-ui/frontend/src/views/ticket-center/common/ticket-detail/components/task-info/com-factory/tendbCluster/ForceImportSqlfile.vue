<template>
  <ImportSqlfile :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import ImportSqlfile from '../common/mysql-import-sqlfile/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.ImportSqlFile>;
  }

  defineProps<Props>();

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_FORCE_IMPORT_SQLFILE,
    inheritAttrs: false,
  });
</script>
