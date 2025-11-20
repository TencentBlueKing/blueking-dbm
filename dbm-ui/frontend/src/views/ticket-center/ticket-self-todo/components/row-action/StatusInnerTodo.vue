<template>
  <TableColumn
    col-key="row-operation"
    fixed="right"
    :title="t('操作')"
    width="80">
    <template #default="{ row }: { row: TicketModel }">
      <BkButton
        :loading="isProcessing"
        text
        theme="primary"
        @click="() => handleGoProcess(row)">
        {{ t('去处理') }}
      </BkButton>
    </template>
  </TableColumn>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getInnerFlowInfo } from '@services/source/ticketFlow';

  import { getBusinessHref } from '@utils';

  defineOptions({
    inheritAttrs: false,
  });

  const { t } = useI18n();
  const router = useRouter();

  const isProcessing = ref(false);

  const handleGoProcess = (row: TicketModel) => {
    isProcessing.value = true;
    getInnerFlowInfo({
      ticket_ids: `${row.id}`,
    })
      .then((data) => {
        if (data[row.id]!.length < 1) {
          const { href } = router.resolve({
            name: 'ticketDetail',
            params: {
              ticketId: row.id,
            },
          });
          window.open(getBusinessHref(href, row.bk_biz_id));
          return;
        }
        const { href } = router.resolve({
          name: 'taskHistoryDetail',
          params: {
            root_id: data[row.id]![0]!.flow_id,
          },
        });
        window.open(href);
      })
      .finally(() => {
        isProcessing.value = false;
      });
  };
</script>
