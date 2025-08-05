<template>
  <div
    ref="templateRef"
    class="task-history-flow-operation-main">
    <div class="title">
      {{ t('确定强制失败吗') }}
    </div>
    <div class="sub-title">{{ t('将会终止节点运行，并置为强制失败状态') }}</div>
    <div class="btn">
      <BkButton
        class="mr-8"
        :loading="isLoading"
        size="small"
        theme="danger"
        @click.stop="handleForceFailClick">
        {{ t('强制失败') }}
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

  import { forceFailflowNode } from '@services/source/taskflow';

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

  const { loading: isLoading, run: runForceFailflowNode } = useRequest(forceFailflowNode, {
    manual: true,
    onSuccess: () => {
      messageSuccess(t('操作成功'));
      emits('close', true);
    },
  });

  const templateRef = ref<HTMLDivElement | null>(null);

  const { t } = useI18n();

  const handleForceFailClick = () => {
    runForceFailflowNode({
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
