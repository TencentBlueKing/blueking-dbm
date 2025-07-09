<template>
  <TableColumn
    col-key="action"
    fixed="right"
    :title="t('操作')"
    :width="100">
    <template #default="{ row }: { row: TicketModel }">
      <ProcessPass :data="row">
        <BkButton
          text
          theme="primary">
          {{ t('通过') }}
        </BkButton>
      </ProcessPass>
      <ProcessRefuse :data="row">
        <BkButton
          class="ml-8"
          text
          theme="primary">
          {{ t('拒绝') }}
        </BkButton>
      </ProcessRefuse>
    </template>
  </TableColumn>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  import TicketModel from '@services/model/ticket/ticket';

  import ProcessPass from '@views/ticket-center/common/action-confirm/ProcessPass.vue';
  import ProcessRefuse from '@views/ticket-center/common/action-confirm/ProcessRefuse.vue';

  defineOptions({
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
