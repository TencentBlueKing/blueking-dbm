<template>
  <BkDialog
    class="batch-edit-dialog"
    :close-icon="false"
    :is-show="isShow"
    :quick-close="false"
    theme="primary"
    :title="$t('批量编辑')"
    width="330"
    @closed="handleClose"
    @confirm="handleConfirm">
    <div
      class="title-spot edit-title"
      style="font-weight: normal;">
      {{ config.title }} <span class="required" />
    </div>
    <BkInput
      v-if="isShowInput"
      v-model="localValue"
      class="input-box"
      :min="1"
      :placeholder="config.placeholder"
      :type="config.type" />
    <MultipleInput
      v-if="config.type === 'textarea'"
      ref="multipleInputRef" />
  </BkDialog>
</template>

<script setup lang="ts">
  import MultipleInput from './MultipleInput.vue';

  interface Props {
    config: {
      type: 'text' | 'number' | 'password' | 'textarea' | string
      title: string,
      placeholder: string,
    }
  }

  interface Emits {
    (e: 'data-change', value: string[], isBatch: boolean): void,
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const isShow = defineModel<boolean>();

  const multipleInputRef = ref();
  const localValue = ref('');

  const isShowInput = computed(() => ['text', 'number', 'password'].includes(props.config.type));

  const handleClose = () => {
    isShow.value = false;
  };

  const handleConfirm = () => {
    if (props.config.type === 'textarea') {
      const data = multipleInputRef.value.getValue();
      if (data.length > 0) {
        emits('data-change', data, true);
      }
    } else {
      emits('data-change', [localValue.value], false);
    }
    localValue.value = '';
    isShow.value = false;
  };
</script>

<style lang="less" scoped>
.batch-edit-dialog {
  .edit-title {
    margin-bottom: 6px;
  }

  .input-box {
    height: 32px;
  }

  :deep(.bk-dialog-header) {
    padding: 14px 16px;

    .bk-dialog-title {
      font-size: 12px !important;
      font-weight: 700;
      color: #63656E;
    }
  }

  :deep(.bk-modal-content) {
    min-height: 20px;
    padding: 0 16px 1px;
  }

  :deep(.bk-modal-footer) {
    height: 38px;
    padding: 0 16px;
    background-color: #fff;
    border-top: none;

    button {
      width: 72px;
      height: 26px;
    }
  }
}
</style>
