<template>
  <div class="bk-editable-input">
    <div
      v-if="slots.prepend"
      class="bk-editable-input-prepend-wrapper">
      <slot name="prepend" />
    </div>
    <BkInput
      v-model="modelValue"
      v-bind="{ ...attrs, ...props }"
      clearable
      @blur="handleBlur"
      @change="handleChange"
      @focus="handleFocus" />
    <div
      v-if="slots.append"
      class="bk-editable-input-append-wrapper">
      <slot name="append" />
    </div>
  </div>
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

  const modelValue = defineModel<string>();

  const slots = defineSlots<{
    prepend?: () => VNode;
    default?: () => VNode;
    append?: () => VNode;
  }>();

  const attrs = useAttrs();
  const columnContext = useColumn();

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
    position: relative;
    display: flex;
    width: 100%;
    overflow: hidden;

    .bk-input {
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

  .bk-editable-input-prepend-wrapper,
  .bk-editable-input-append-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 8px;
    user-select: none;
  }

  .bk-editable-input-prepend-wrapper {
    padding-left: 10px;
  }

  .bk-editable-input-append-wrapper {
    padding-right: 10px;
    margin-left: auto;
  }
</style>
