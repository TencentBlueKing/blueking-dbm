<template>
  <BkInput
    v-model="modelValue"
    class="bk-editable-input"
    v-bind="{ ...attrs, ...props }"
    clearable
    @blur="handleBlur"
    @change="handleChange"
    @focus="handleFocus" />
</template>
<script setup lang="ts">
  import { useAttrs, watch } from 'vue';

  import useColumn from '../useColumn';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    placeholder?: string;
    prefix?: string;
    suffix?: string;
    maxlength?: number;
    minlength?: number;
  }

  interface Emits {
    (e: 'blur'): void;
    (e: 'focus'): void;
    (e: 'change', params: string): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const attrs = useAttrs();

  const columnContext = useColumn();

  const modelValue = defineModel<string>();

  watch(modelValue, () => {
    columnContext?.validate('change');
  });

  const handleChange = (value: string) => {
    emits('change', value);
  };
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
    &.bk-input {
      height: 40px;
      border: none;
      box-shadow: none !important;

      .bk-input--text {
        background: transparent;
      }

      .bk-input--suffix-icon {
        background: transparent;
      }
    }
  }
</style>
