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
      #optionRender="{ item }">
      <slot
        :item="item"
        name="option" />
    </template>
    <template v-if="slots.default">
      <slot />
    </template>
    <template
      v-if="slots.trigger"
      #trigger="{ selected }">
      <slot
        name="trigger"
        :selected="selected" />
    </template>
    <template
      v-if="slots.allOptionIcon"
      #allOptionIcon>
      <slot name="allOptionIcon" />
    </template>
    <template
      v-if="slots.tagRender"
      #tagRender="{ label, value }">
      <slot
        :label="label"
        name="tagRender"
        :value="value" />
    </template>
    <template
      v-if="slots.tag"
      #tag="{ selected }">
      <slot
        name="tag"
        :selected="selected" />
    </template>
  </BkSelect>
</template>
<script lang="ts">
  /* eslint-disable vue/no-unused-properties */
  interface Props {
    clearable?: boolean;
    disabled?: boolean;
    filterable?: boolean;
    multiple?: boolean;
    placeholder?: string;
    popoverOptions?: Record<string, any>;
  }
</script>
<script setup lang="ts" generic="T extends string[] | number[] | string | number">
  import { useAttrs, type VNode, watch } from 'vue';

  import useColumn from '../useColumn';

  type ISelected = {
    label: string;
    value: number | string;
  };

  const props = defineProps<Props>();

  const emits = defineEmits<{
    (e: 'blur' | 'focus'): void;
    (e: 'change', value: T): void;
  }>();

  const slots = defineSlots<{
    allOptionIcon?: () => VNode;
    default?: () => VNode;
    option?: (value: { item: Record<string, any> }) => VNode;
    tag?: (value: { selected: ISelected[] }) => VNode;
    tagRender?: (item: ISelected) => VNode;
    trigger?: (value: { selected: ISelected[] }) => VNode;
  }>();

  const modelValue = defineModel<T>();

  const attrs = useAttrs();

  const columnContext = useColumn();

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
    &.bk-select {
      width: 100%;

      .bk-input {
        height: 40px;
        border: none;
        box-shadow: none !important;
      }

      .bk-input--text {
        background: transparent;
      }

      .bk-select-trigger {
        height: 40px !important;

        .bk-select-tag {
          height: 40px !important;
          background: transparent;
          border: none !important;
          box-shadow: none !important;
        }
      }
    }
  }
</style>
