<template>
  <BkButton
    :loading="isProcessing"
    text
    theme="primary"
    @click="handleGoProcess">
    {{ t('去处理') }}
  </BkButton>
  <BkButton
    class="ml-8"
    text
    theme="primary"
    @click="handleGoDetail">
    {{ t('查看详情') }}
  </BkButton>
</template>
<script setup lang="ts">
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';
  import { useRouter } from 'vue-router';

  import TicketModel from '@services/model/ticket/ticket';
  import { getInnerFlowInfo } from '@services/source/ticketFlow';

  interface Props {
    data: TicketModel;
  }

  interface Emits {
    (e: 'go-ticket-detail', params: TicketModel): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  defineOptions({
    inheritAttrs: false,
  });

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
          emits('go-ticket-detail', props.data);
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

  const handleGoDetail = () => {
    emits('go-ticket-detail', props.data);
  };
</script>
