<template>
  <BkTable
    :data="ticketDetails.details.infos"
    show-overflow-tooltip>
    <BkTableColumn :label="t('目标集群')">
      <template #default="{ data }: { data: RowData }">
        {{ ticketDetails.details.clusters[data.cluster_id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('源 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag v-if="data">{{ data.from_database }}</BkTag>
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('新 DB 名')">
      <template #default="{ data }: { data: RowData }">
        <BkTag v-if="data">{{ data.to_database }}</BkTag>
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<Mysql.HaRenameDatabase>;
  }

  type RowData = Props['ticketDetails']['details']['infos'][number];

  defineProps<Props>();

  const { t } = useI18n();
</script>
