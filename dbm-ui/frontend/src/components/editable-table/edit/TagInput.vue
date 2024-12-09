<template>
  <BkTagInput
    v-model="modelValue"
    allow-create
    class="bk-editable-tag-input"
    v-bind="{ ...attrs, ...props }"
    clearable
    has-delete-icon
    @blur="handleBlur"
    @focus="handleFocus" />
</template>
<script setup lang="ts">
  import { watch } from 'vue';

  import useColumn from '../useColumn';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    placeholder?: string;
    maxData?: number;
  }

  interface Emits {
    (e: 'blur'): void;
    (e: 'focus'): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const attrs = useAttrs();

  const columnContext = useColumn();

  const modelValue = defineModel<string[]>();

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
  .bk-editable-tag-input {
    &.bk-tag-input {
      width: 100%;

      .bk-tag-input-trigger {
        background: transparent;
        border: none;
        border-radius: 0;
      }
    }
  }
</style>
