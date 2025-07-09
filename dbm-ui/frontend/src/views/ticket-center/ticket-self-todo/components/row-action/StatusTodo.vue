<template>
  <TableColumn
    col-key="action"
    fixed="right"
    :title="t('操作')"
    :width="140">
    <template #default="{ row }: { row: TicketModel }">
      <ProcessApproveExce :data="row">
        <BkButton
          text
          theme="primary">
          {{ t('确认执行') }}
        </BkButton>
      </ProcessApproveExce>
      <ProcessTerminate :data="row">
        <BkButton
          class="ml-8"
          text
          theme="primary">
          {{ t('终止单据') }}
        </BkButton>
      </ProcessTerminate>
    </template>
  </TableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import ProcessApproveExce from '@views/ticket-center/common/action-confirm/ProcessApproveExce.vue';
  import ProcessTerminate from '@views/ticket-center/common/action-confirm/ProcessTerminate.vue';

  defineOptions({
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
