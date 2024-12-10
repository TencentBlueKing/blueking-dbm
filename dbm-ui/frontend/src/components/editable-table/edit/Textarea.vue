<template>
  <BkInput
    v-model="modelValue"
    autosize
    class="bk-editable-input"
    :resize="false"
    type="textarea"
    v-bind="{ ...attrs, ...props }"
    @blur="handleBlur"
    @focus="handleFocus" />
</template>
<script setup lang="ts">
  import { useAttrs, watch } from 'vue';

  import useColumn from '../useColumn';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    placeholder?: string;
    maxlength?: number;
    minlength?: number;
  }

  interface Emits {
    (e: 'blur'): void;
    (e: 'focus'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const attrs = useAttrs();

  const columnContext = useColumn();

  const modelValue = defineModel<string>();

  watch(modelValue, () => {
    columnContext?.validate('change');
  });

  const handleBlur = () => {
    columnContext?.blur();
    columnContext?.validate('blur');
    emits('blur');
  };

  const handleFocus = () => {
    columnContext?.focus();
    emits('focus');
  };
</script>
<style lang="less">
  .bk-editable-input {
    &.bk-textarea {
      min-height: 40px;
      padding-top: 6px;
      background: transparent;
      border: none;
      border-radius: none;
      box-shadow: none !important;

      textarea {
        background: transparent;
      }
    }
  }
</style>
