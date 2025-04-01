<template>
  <BkButton
    :loading="isProcessing"
    text
    theme="primary"
    @click="handleGoProcess">
    {{ t('去处理') }}
  </BkButton>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getInnerFlowInfo } from '@services/source/ticketFlow';

  import { getBusinessHref } from '@utils';

  interface Props {
    data: TicketModel;
  }

  defineOptions({
    inheritAttrs: false,
  });
  const props = defineProps<Props>();

  const { t } = useI18n();
  const router = useRouter();

  const isProcessing = ref(false);

  const handleGoProcess = () => {
    isProcessing.value = true;
    getInnerFlowInfo({
      ticket_ids: `${props.data.id}`,
    })
      .then((data) => {
        if (data[props.data.id].length < 1) {
          const { href } = router.resolve({
            name: 'ticketDetail',
            params: {
              ticketId: props.data.id,
            },
          });
          window.open(getBusinessHref(href, props.data.bk_biz_id));
          return;
        }
        const { href } = router.resolve({
          name: 'taskHistoryDetail',
          params: {
            root_id: data[props.data.id][0].flow_id,
          },
        });
        window.open(href);
      })
      .finally(() => {
        isProcessing.value = false;
      });
  };
</script>
