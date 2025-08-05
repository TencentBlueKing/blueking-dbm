<template>
  <div
    ref="templateRef"
    class="task-history-flow-operation-main">
    <div class="title">
      {{ t('确认跳过当前节点继续执行？') }}
    </div>
    <div class="sub-title">{{ t('将会忽略当前节点，继续往下执行') }}</div>
    <div class="btn">
      <BkButton
        class="mr-8"
        :loading="skipLoading"
        size="small"
        theme="primary"
        @click.stop="handleSkipClick">
        {{ t('跳过节点') }}
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

  import { skipTaskflowNode } from '@services/source/taskflow';

  import { messageSuccess } from '@utils';

  import { type Node } from '../../utils';

  interface Props {
    data?: Node;
    rootId: string;
  }

  type Emits = (e: 'close', refresh: boolean) => void;

  const props = withDefaults(defineProps<Props>(), {
    data: undefined,
    isShow: false,
  });
  const emits = defineEmits<Emits>();

  const { loading: skipLoading, run: runSkipTaskflowNode } = useRequest(skipTaskflowNode, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      emits('close', true);
    },
  });

  const templateRef = ref<HTMLDivElement | null>(null);

  const { t } = useI18n();

  const handleSkipClick = () => {
    runSkipTaskflowNode({
      node_id: props.data!.id,
      root_id: props.rootId,
    });
  };

  defineExpose({
    getTemplateRef() {
      return templateRef.value;
    },
  });
</script>
