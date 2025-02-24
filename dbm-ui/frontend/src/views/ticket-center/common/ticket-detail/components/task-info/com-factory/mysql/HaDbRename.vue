<template>
  <DBRename :ticket-details="ticketDetails" />
  <InfoList>
    <InfoItem :label="t('忽略业务连接：')">
      {{ ticketDetails.details.force ? t('是') : t('否') }}
    </InfoItem>
  </InfoList>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel, { type Mysql } from '@services/model/ticket/ticket';

  import { TicketTypes } from '@/common/const';

  import InfoList, { Item as InfoItem } from '../components/info-list/Index.vue';

  import DBRename from './common/DBRename.vue';

  interface Props {
    ticketDetails: TicketModel<Mysql.HaRenameDatabase>;
  }

  defineOptions({
    name: TicketTypes.MYSQL_HA_RENAME_DATABASE,
    inheritAttrs: false,
  });

  defineProps<Props>();

  const { t } = useI18n();
</script>
