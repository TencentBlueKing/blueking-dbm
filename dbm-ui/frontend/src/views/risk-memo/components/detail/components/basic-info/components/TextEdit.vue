<template>
  <div
    class="text-edit-value-main"
    :class="{ 'is-error': isError }">
    <div
      v-if="!isEdit"
      class="display-mian">
      <div class="value-display">
        {{ localValue }}
      </div>
      <DbIcon
        v-if="!readonly"
        class="edit-main"
        type="edit"
        @click="handleClickEdit" />
    </div>
    <BkInput
      v-else
      ref="editValueRef"
      v-model="localValue"
      class="value-edit-main"
      :resize="false"
      :rows="3"
      :type="textArea ? 'textarea' : 'input'"
      @blur="handleBlur"
      @input="handleInput" />
    <DbIcon
      v-if="isError"
      v-bk-tooltips="t('不能为空')"
      class="error-icon"
      type="exclamation-fill" />
  </div>
</template>
<script setup lang="ts">
  import { useI18n } from 'vue-i18n';

  interface Props {
    readonly?: boolean;
    textArea?: boolean;
    value?: string;
  }

  type Emits = (e: 'change', value: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    readonly: false,
    textArea: false,
    value: '',
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();

  const editValueRef = ref<any>(null);
  const isEdit = ref(false);
  const localValue = ref('');
  const isError = ref(false);

  watch(
    () => props.value,
    () => {
      localValue.value = props.value;
    },
    {
      immediate: true,
    },
  );

  const handleClickEdit = () => {
    isEdit.value = true;
    setTimeout(() => {
      editValueRef.value?.focus();
    });
  };

  const handleInput = () => {
    isError.value = false;
  };

  const handleBlur = () => {
    if (!localValue.value) {
      isError.value = true;
      return;
    }
    if (props.value !== localValue.value) {
      emits('change', localValue.value);
    }
    isEdit.value = false;
  };
</script>
<style lang="less">
  .text-edit-value-main {
    width: 100%;
    display: flex;
    align-items: center;
    font-size: 12px;
    position: relative;

    &.is-error {
      .value-edit-main {
        border-color: #ea3636;
      }
    }

    .display-mian {
      width: 100%;
      display: flex;
      align-items: center;

      &:hover {
        .edit-main {
          display: block;
        }
      }

      .value-display {
        flex: 1;
        flex-grow: 0;
        flex-shrink: 1;
        flex-basis: auto;
        max-width: calc(100% - 20px);
        overflow-wrap: break-word;
      }

      .edit-main {
        width: 12px;
        height: 12px;
        color: #979ba5;
        font-size: 12px;
        cursor: pointer;
        margin-left: 4px;
        display: none;

        &:hover {
          color: #3a84ff;
        }
      }
    }

    .value-edit-main {
      width: 100%;
    }

    .error-icon {
      position: absolute;
      top: 50%;
      transform: translateY(-50%);
      right: 8px;
      color: #ea3636;
      font-size: 14px;
      cursor: pointer;
    }
  }
</style>
