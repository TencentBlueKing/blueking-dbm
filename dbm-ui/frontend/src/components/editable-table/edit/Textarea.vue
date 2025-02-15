<template>
  <div class="bk-editable-textarea">
    <div
      v-if="slots.prepend"
      class="bk-editable-textarea-prepend-wrapper">
      <slot name="prepend" />
    </div>
    <BkInput
      v-model="modelValue"
      autosize
      clearable
      :resize="false"
      v-bind="{ ...attrs, ...props }"
      type="textarea"
      @blur="handleBlur"
      @change="handleChange"
      @focus="handleFocus" />
    <div
      v-if="slots.append"
      class="bk-editable-textarea-append-wrapper">
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
    maxlength?: number;
    minlength?: number;
    rows?: number;
  }

  interface Emits {
    (e: 'blur' | 'focus'): void;
    (e: 'change', value: string): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const slots = defineSlots<{
    prepend?: () => VNode;
    default?: () => VNode;
    append?: () => VNode;
  }>();

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

  const handleChange = (value: string) => {
    emits('change', value);
  };
</script>
<style lang="less">
  .bk-editable-textarea {
    position: relative;
    display: flex;
    width: 100%;
    overflow: hidden;

    .bk-textarea {
      min-height: 40px;
      padding-top: 6px;
      background: transparent;
      border: none;
      border-radius: 0;
      box-shadow: none !important;
      flex-direction: row;

      textarea {
        background: transparent;
      }

      .bk-textarea--suffix-icon {
        align-items: center;
      }
    }
  }

  .bk-editable-textarea-prepend-wrapper,
  .bk-editable-textarea-append-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 8px;
    user-select: none;
  }

  .bk-editable-textarea-prepend-wrapper {
    padding-left: 10px;
  }

  .bk-editable-textarea-append-wrapper {
    padding-right: 10px;
    margin-left: auto;
  }
</style>
