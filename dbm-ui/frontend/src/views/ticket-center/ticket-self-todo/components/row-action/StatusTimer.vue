<template>
  <!-- 必须包在 TableColumn 里才会注册成表格列；行数据从作用域插槽取，RowAction 不传 data -->
  <TableColumn
    col-key="row-operation"
    fixed="right"
    :min-width="130"
    :title="t('操作')">
    <template #default="{ row }: { row: TicketModel }">
      <ProcessTimerExce :data="row">
        <BkButton
          text
          theme="primary">
          {{ t('立即执行') }}
        </BkButton>
      </ProcessTimerExce>
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

  import ProcessTerminate from '@views/ticket-center/common/action-confirm/ProcessTerminate.vue';
  import ProcessTimerExce from '@views/ticket-center/common/action-confirm/ProcessTimerExce.vue';

  defineOptions({
    inheritAttrs: false,
  });

  const { t } = useI18n();
</script>
