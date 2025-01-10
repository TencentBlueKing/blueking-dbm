<template>
  <!-- prettier-ignore -->
  <BkTagInput
    v-model="(modelValue as string[])"
    v-bind="{ ...attrs, ...props }"
    allow-auto-match
    allow-create
    class="bk-editable-tag-input"
    clearable
    has-delete-icon
    @blur="handleBlur"
    @focus="handleFocus" />
</template>
<script setup lang="ts" generic="T extends string[] | number[] | string | number">
  import { watch } from 'vue';

  import useColumn from '../useColumn';

  /* eslint-disable vue/no-unused-properties */
  export interface Props {
    placeholder?: string;
    maxData?: number;
  }

  export interface Emits<T> {
    (e: 'blur' | 'focus'): void;
    (e: 'change', value: T): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits<T>>();

  const attrs = useAttrs();

  const columnContext = useColumn();

  const modelValue = defineModel<T>();

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
        min-height: 40px;
        background: transparent;
        border: none;
        border-radius: 0;

        .placeholder {
          top: 50%;
          height: auto;
          transform: translateY(-50%);
        }

        .tag-input {
          background: transparent;
        }
      }
    }
  }
</style>
