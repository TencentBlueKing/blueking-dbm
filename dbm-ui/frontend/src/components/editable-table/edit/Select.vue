<template>
  <BkSelect
    v-model="modelValue"
    class="bk-editable-select"
    v-bind="{ ...attrs, ...props }"
    @blur="handleBlur"
    @change="handleChange"
    @focus="handleFocus">
    <template
      v-if="slots.option"
      #optionRender="{ item, index }">
      <slot
        :index="index"
        :item="item"
        name="option" />
    </template>
    <template
      v-if="slots.trigger"
      #trigger="{ selected }">
      <slot
        name="trigger"
        :selected="selected" />
    </template>
  </BkSelect>
</template>
<script lang="ts">
  /* eslint-disable vue/no-unused-properties */
  interface Props {
    placeholder?: string;
    disabled?: boolean;
    multiple?: boolean;
    filterable?: boolean;
    popoverOptions?: Record<string, any>;
    clearable?: boolean;
  }
</script>
<script setup lang="ts" generic="T extends string[] | number[] | string | number">
  import { useAttrs, watch } from 'vue';

  import useColumn from '../useColumn';

  const props = defineProps<Props>();

  const emits = defineEmits<{
    (e: 'blur'): void;
    (e: 'focus'): void;
    (e: 'change', value: T): void;
  }>();

  const slots = defineSlots<{
    trigger?: (value: { selected: any[] }) => VNode;
    option?: (value: { item: Record<string, any>; index: number }) => VNode;
  }>();

  const attrs = useAttrs();

  const columnContext = useColumn();

  const modelValue = defineModel<T>();

  watch(modelValue, () => {
    columnContext?.validate('change');
  });

  const handleChange = (value: T) => {
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
  .bk-editable-select {
    width: 100%;

    .bk-input {
      height: 40px;
      border: none;
      box-shadow: none !important;
    }

    .bk-input--text {
      background: transparent;
    }
  }
</style>
