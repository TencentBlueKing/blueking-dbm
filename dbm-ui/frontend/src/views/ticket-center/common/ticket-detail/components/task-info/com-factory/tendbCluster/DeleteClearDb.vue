<template>
  <ImportSqlfile :ticket-details="ticketDetails" />
</template>
<script setup lang="ts">
  import TicketModel, { type TendbCluster } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import ImportSqlfile from '../common/mysql-import-sqlfile/Index.vue';

  interface Props {
    ticketDetails: TicketModel<TendbCluster.DeleteClearDb>;
  }

  defineOptions({
    name: TicketTypes.TENDBCLUSTER_DELETE_CLEAR_DB,
    inheritAttrs: false,
  });

  defineProps<Props>();
</script>
