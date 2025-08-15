<template>
  <div
    ref="templateRef"
    class="task-history-flow-operation-main">
    <div class="title">
      {{ t('确认重试当前失败节点？') }}
    </div>
    <div class="sub-title">{{ t('重试将重新执行当前节点') }}</div>
    <div class="btn">
      <BkButton
        class="mr-8"
        :loading="retryLoading"
        size="small"
        theme="primary"
        @click.stop="handleRetryClick">
        {{ t('确认重试') }}
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

  import { retryTaskflowNode } from '@services/source/taskflow';

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

  const { loading: retryLoading, run: runRetryTaskflowNode } = useRequest(retryTaskflowNode, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      emits('close', true);
    },
  });

  const templateRef = ref<HTMLDivElement | null>(null);

  const { t } = useI18n();

  const handleRetryClick = () => {
    runRetryTaskflowNode({
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
