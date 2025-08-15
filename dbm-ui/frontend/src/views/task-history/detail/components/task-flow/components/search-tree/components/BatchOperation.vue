<template>
  <div class="batch-operation-main">
    <BkCheckbox
      v-model="isCheckAll"
      class="operation-checkbox"
      @change="handleChangeAll">
      {{ t('全选') }}
    </BkCheckbox>
    <div class="btn-operations">
      <BkPopConfirm
        v-if="status === 'RUNNING'"
        :confirm-config="{
          theme: 'danger',
        }"
        :confirm-text="t('批量失败')"
        :content="t('强制失败将立即终止这n个节点运行，统一标记为 “失败”', { n: data.length })"
        :popover-options="{
          disabled: isDisabled,
        }"
        :title="t('确认强制终止n个节点并置为失败？', { n: data.length })"
        trigger="click"
        width="280"
        @confirm="handleConfirmForceFail">
        <BkButton
          :disabled="isDisabled"
          :loading="isForceFailLoading"
          theme="danger">
          {{ t('批量失败') }}
        </BkButton>
      </BkPopConfirm>
      <template v-else-if="status === 'FAILED'">
        <BkPopConfirm
          :confirm-text="t('批量重试')"
          :content="t('重试将重新执行这n个节点', { n: data.length })"
          :popover-options="{
            disabled: isDisabled,
          }"
          :title="t('确认重试n个失败节点？', { n: data.length })"
          trigger="click"
          width="280"
          @confirm="handleConfirmRetry">
          <BkButton
            :disabled="isDisabled"
            :loading="isRetryLoading"
            theme="primary">
            {{ t('批量重试') }}
          </BkButton>
        </BkPopConfirm>
        <BkPopConfirm
          :confirm-text="t('批量跳过')"
          :content="
            t('跳过将忽略这n个节点的失败状态，直接执行后续节点，当前节点将被标记为 “已跳过”', { n: data.length })
          "
          :popover-options="{
            disabled: isDisabled,
          }"
          :title="t('确认跳过n个失败节点？', { n: data.length })"
          trigger="click"
          width="280"
          @confirm="handleConfirmSkip">
          <BkButton
            :disabled="isDisabled"
            :loading="isSkipLoading"
            outline
            theme="primary">
            {{ t('批量跳过') }}
          </BkButton>
        </BkPopConfirm>
      </template>
      <template v-else>
        <BkPopConfirm
          :confirm-text="t('批量继续')"
          :content="t('继续后将立即完成这n个节点，并执行后续节点', { n: data.length })"
          :popover-options="{
            disabled: isDisabled,
          }"
          :title="t('确认继续执行n个待继续节点？', { n: data.length })"
          trigger="click"
          width="280"
          @confirm="handleConfirmTodo">
          <BkButton
            :disabled="isDisabled"
            :loading="isTodoLoading"
            theme="primary">
            {{ t('批量继续') }}
          </BkButton>
        </BkPopConfirm>
        <BkPopConfirm
          :confirm-config="{
            theme: 'danger',
          }"
          :confirm-text="t('批量失败')"
          :content="t('强制失败将立即终止这n个节点运行，统一标记为 “失败”', { n: data.length })"
          :popover-options="{
            disabled: isDisabled,
          }"
          :title="t('确认强制终止n个节点并置为失败？', { n: data.length })"
          trigger="click"
          width="280"
          @confirm="handleConfirmForceFail">
          <BkButton
            :disabled="isDisabled"
            :loading="isForceFailLoading"
            theme="danger">
            {{ t('批量失败') }}
          </BkButton>
        </BkPopConfirm>
      </template>
      <BkButton
        v-if="data.length"
        :disabled="isDisabled"
        @click="handleClickCancel">
        {{ t('取消') }}
      </BkButton>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';
  import { useRequest } from 'vue-request';

  import { batchForceFailTaskflowNode, batchRetryNodes, batchSkipTaskflowNode } from '@services/source/taskflow';
  import { batchProcessTodo } from '@services/source/ticketFlow';

  import { messageSuccess } from '@utils';

  import { type TreeNode } from '../../flow-canvas/utils';

  interface Props {
    data: TreeNode[];
    rootId: string;
    status: string;
  }

  interface Emits {
    (e: 'cancel'): void;
    (e: 'checkAll', isCheck: boolean): void;
    (e: 'refresh'): void;
  }

  interface Exposes {
    setCheckAll(isCheck: boolean): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const isCheckAll = ref(false);

  const isDisabled = computed(() => !props.data.length);

  const handleSuccess = () => {
    isCheckAll.value = false;
    messageSuccess(t('操作成功'));
    emits('refresh');
  };

  const { loading: isTodoLoading, run: runBatchProcessTodo } = useRequest(batchProcessTodo, {
    manual: true,
    onSuccess() {
      handleSuccess();
    },
  });

  const { loading: isRetryLoading, run: runBatchRetryNodes } = useRequest(batchRetryNodes, {
    manual: true,
    onSuccess() {
      handleSuccess();
    },
  });

  const { loading: isSkipLoading, run: runBatchSkipTaskflowNode } = useRequest(batchSkipTaskflowNode, {
    manual: true,
    onSuccess() {
      handleSuccess();
    },
  });

  const { loading: isForceFailLoading, run: runBatchForceFailTaskflowNode } = useRequest(batchForceFailTaskflowNode, {
    manual: true,
    onSuccess() {
      handleSuccess();
    },
  });

  const handleConfirmForceFail = () => {
    runBatchForceFailTaskflowNode({
      nodes: props.data.map((item) => item.id),
      root_id: props.rootId,
    });
  };

  const handleConfirmTodo = () => {
    runBatchProcessTodo({
      action: 'APPROVE',
      operations: props.data.map((item) => ({
        params: {},
        todo_id: item.todoId,
      })),
    });
  };

  const handleConfirmSkip = () => {
    runBatchSkipTaskflowNode({
      nodes: props.data.map((item) => item.id),
      root_id: props.rootId,
    });
  };

  const handleConfirmRetry = () => {
    runBatchRetryNodes({
      nodes: props.data.map((item) => item.id),
      root_id: props.rootId,
    });
  };

  const handleChangeAll = (isCheck: boolean) => {
    emits('checkAll', isCheck);
  };

  const handleClickCancel = () => {
    emits('cancel');
    isCheckAll.value = false;
  };

  defineExpose<Exposes>({
    setCheckAll(isCheck: boolean) {
      isCheckAll.value = isCheck;
    },
  });
</script>
<style lang="less">
  .batch-operation-main {
    display: flex;
    width: calc(100% + 24px);
    height: 48px;
    min-height: 48px;
    padding: 0 12px;
    margin-top: 6px;
    margin-left: -12px;
    border: 1px solid #dcdee5;
    align-items: center;
    justify-content: space-between;

    .operation-checkbox {
      min-width: 48px;
    }

    .btn-operations {
      display: flex;
      gap: 8px;
    }
  }
</style>
