<template>
  <InfoList>
    <InfoItem :label="t('源集群')">
      {{ ticketDetails.details.clusters[ticketDetails.details.cluster_id].immute_domain }}
    </InfoItem>
    <InfoItem :label="t('导出方式')">
      {{ ticketDetails.details.where ? t('条件导出') : t('整表导出') }}
    </InfoItem>
    <InfoItem :label="t('目标DB名')">
      <TagBlock :data="ticketDetails.details.databases" />
    </InfoItem>
    <InfoItem :label="t('目标表名')">
      <TagBlock :data="ticketDetails.details.tables" />
    </InfoItem>
    <InfoItem
      v-if="ticketDetails.details.tables.length === 1 && ticketDetails.details.tables[0] === '*'"
      :label="t('忽略表名')">
      <TagBlock :data="ticketDetails.details.tables_ignore" />
    </InfoItem>
    <InfoItem :label="t('where 条件')">
      {{ ticketDetails.details.where || '--' }}
    </InfoItem>
    <InfoItem :label="t('导出物')">
      <template v-if="ticketDetails.details.dump_data && ticketDetails.details.dump_schema">
        {{ t('数据和表结构') }}
      </template>
      <template v-else-if="ticketDetails.details.dump_data && !ticketDetails.details.dump_schema">
        {{ t('仅数据') }}
      </template>
      <template v-else>{{ t('仅表结构') }}</template>
    </InfoItem>
  </InfoList>
</template>

<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import TagBlock from '@components/tag-block/Index.vue';

  import InfoList, { Item as InfoItem } from '../../components/info-list/Index.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.DumpData>;
  }

  defineProps<Props>();

  const { t } = useI18n();
</script>
