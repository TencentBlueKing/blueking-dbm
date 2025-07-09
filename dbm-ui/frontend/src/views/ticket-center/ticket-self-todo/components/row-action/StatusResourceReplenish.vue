<template>
  <TableColumn
    col-key="row-operation"
    fixed="right"
    :title="t('操作')"
    :width="120">
    <template #default="{ row }: { row: TicketModel }">
      <ProcessResourceReplenish :data="row">
        <BkButton
          text
          theme="primary">
          {{ t('重试') }}
        </BkButton>
      </ProcessResourceReplenish>
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

  import ProcessResourceReplenish from '@views/ticket-center/common/action-confirm/ProcessResourceReplenish.vue';
  import ProcessTerminate from '@views/ticket-center/common/action-confirm/ProcessTerminate.vue';

  defineOptions({
    inheritAttrs: false,
  });
  const { t } = useI18n();
</script>
