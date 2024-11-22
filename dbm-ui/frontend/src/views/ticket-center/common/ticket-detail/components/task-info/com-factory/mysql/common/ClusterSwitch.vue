<template>
  <BkTable :data="ticketDetails.details.cluster_ids.map((id) => ({ id }))">
    <BkTableColumn
      field="id"
      :label="t('集群 ID')" />
    <BkTableColumn :label="t('集群名称')">
      <template #default="{ data }: { data: { id: number } }">
        {{ ticketDetails.details.clusters[data.id].immute_domain }}
      </template>
    </BkTableColumn>
    <BkTableColumn :label="t('集群类型')">
      <template #default="{ data }: { data: { id: number } }">
        {{ ticketDetails.details.clusters[data.id].cluster_type_name }}
      </template>
    </BkTableColumn>
  </BkTable>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  interface Props {
    ticketDetails: TicketModel<Mysql.ClusterSwitch>;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
