<template>
  <div
    ref="templateRef"
    class="task-history-flow-operation-main">
    <div class="title">
      {{ t('确认继续执行？') }}
    </div>
    <div class="sub-title">{{ t('将会立即执行该节点') }}</div>
    <div class="btn">
      <BkButton
        class="mr-8"
        :loading="continueLoading"
        size="small"
        theme="primary"
        @click.stop="handleContinueClick">
        {{ t('继续执行') }}
      </BkButton>
      <BkButton
        size="small"
        @click.stop="() => emits('close', false)">
        {{ t('取消') }}
      </BkButton>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { ticketBatchProcessTodo } from '@services/source/ticket';

  import { messageSuccess } from '@utils';

  import { type Node } from '../../utils';

  interface Props {
    data?: Node;
  }

  type Emits = (e: 'close', refresh: boolean) => void;

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    isShow: false,
  });
  const emits = defineEmits<Emits>();

  const { loading: continueLoading, run: runApproveTaskflowNode } = useRequest(ticketBatchProcessTodo, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      emits('close', true);
    },
  });

  const templateRef = ref<HTMLDivElement | null>(null);

  const { t } = useI18n();

  const handleContinueClick = () => {
    if (props.data && props.data.todoId) {
      runApproveTaskflowNode({
        action: 'APPROVE',
        operations: [
          {
            params: {},
            todo_id: props.data.todoId,
          },
        ],
      });
    }
  };

  defineExpose({
    getTemplateRef() {
      return templateRef.value;
    },
  });
</script>
