<template>
  <Component
    :is="renderCom"
    :data="data">
    <template
      v-if="
        [
          TicketTypes.MYSQL_IMPORT_SQLFILE,
          TicketTypes.SQLSERVER_IMPORT_SQLFILE,
          TicketTypes.TENDBCLUSTER_IMPORT_SQLFILE,
          TicketTypes.TENDBCLUSTER_FORCE_IMPORT_SQLFILE,
        ].includes(ticketDetail.ticket_type)
      "
      #contentPreppend>
      <!-- prettier-ignore -->
      <SqlGrammarCheck :ticket-detail="(ticketDetail as MySQLImportSQLFileTicekt)" />
    </template>
  </Component>
</template>
<script setup lang="ts">
  import FlowMode from '@services/model/ticket/flow';
  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@common/const';

  import FlowTypeCommon from '../flow-type-common/index';

  import SqlGrammarCheck from './components/SqlGrammarCheck.vue';

  interface Props {
    data: FlowMode<unknown>;
    ticketDetail: TicketModel<unknown>;
  }

  type MySQLImportSQLFileTicekt = TicketModel<Mysql.ImportSqlFile>;

  const props = defineProps<Props>();

  defineOptions({
    name: FlowMode.TYPE_DELIVERY,
    inheritAttrs: false,
  });

  const renderCom = FlowTypeCommon[props.data.status] || '';
</script>
