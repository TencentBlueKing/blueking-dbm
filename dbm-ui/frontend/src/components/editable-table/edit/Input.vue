<template>
  <div class="bk-editable-input">
    <div
      v-if="slots.prepend"
      class="bk-editable-input-prepend-wrapper">
      <slot name="prepend" />
    </div>
    <BkInput
      v-bind="{ ...attrs, ...props }"
      ref="inputRef"
      v-model="modelValue"
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
  import { useAttrs, type VNode, watch } from 'vue';

  import useColumn from '../useColumn';

  /* eslint-disable vue/no-unused-properties */
  interface Props {
    maxlength?: number;
    minlength?: number;
    placeholder?: string;
    prefix?: string;
    suffix?: string;
  }

  interface Emits {
    (e: 'blur' | 'focus'): void;
    (e: 'change', params: string): void;
  }

  interface Exposes {
    focus(): void;
  }

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const slots = defineSlots<{
    append?: () => VNode;
    default?: () => VNode;
    prepend?: () => VNode;
  }>();

  const modelValue = defineModel<string | number>();

  const attrs = useAttrs();
  const columnContext = useColumn();
  const inputRef = ref();

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

  defineExpose<Exposes>({
    focus() {
      inputRef.value?.focus();
    },
  });
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
