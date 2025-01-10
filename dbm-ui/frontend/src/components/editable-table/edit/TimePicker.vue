<template>
  <BkTimePicker
    v-model="modelValue"
    append-to-body
    class="bk-editable-time-picker"
    v-bind="{ ...attrs, ...props }"
    @blur="handleBlur"
    @change="handleChange"
    @focus="handleFocus" />
</template>
<script lang="ts">
  /* eslint-disable vue/no-unused-properties */
  interface Props {
    placeholder?: string;
    type?: 'time' | 'timerange';
    format?: string;
    multiple?: boolean;
    disabledDate?: (date: Date | number) => boolean;
  }
</script>
<script setup lang="ts" generic="T extends [string, string] | [Date, Date] | string | Date">
  import { useAttrs, watch } from 'vue';

  import useColumn from '../useColumn';

  const props = defineProps<Props>();
  const emits = defineEmits<{
    (e: 'blur'): void;
    (e: 'focus'): void;
    (e: 'change', value: T): void;
  }>();

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

  const handleChange = (value: T) => {
    emits('change', value);
  };
</script>
<style lang="less">
  .bk-editable-time-picker {
    &.bk-date-picker {
      width: 100%;

      .icon-wrapper {
        height: 40px;
      }

      .bk-date-picker-editor {
        height: 40px;
        background: transparent;
        border: none;

        &:focus {
          border: none;
        }
      }
    }
  }
</style>
