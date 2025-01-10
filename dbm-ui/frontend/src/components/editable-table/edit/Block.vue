<template>
  <div
    class="bk-editable-text"
    @blur="handleBlur"
    @focus="handleFocus">
    <div
      v-if="slots.prepend"
      class="bk-editable-text-prepend-wrapper">
      <slot name="prepend" />
    </div>
    <div
      class="bk-editable-text-content-wrapper"
      :class="{
        'is-show-prepend': Boolean(slots.prepend),
        'is-show-append': Boolean(slots.append),
      }">
      <span ref="content">
        <slot>
          {{ modelValue }}
        </slot>
      </span>
      <div
        v-if="isShowPlacehoder"
        class="bk-editable-text-content-placeholder">
        {{ placeholder }}
      </div>
    </div>
    <div
      v-if="slots.append"
      class="bk-editable-text-append-wrapper">
      <slot name="append" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { nextTick, onMounted, onUpdated, ref, useTemplateRef, type VNode, watch } from 'vue';

  import useColumn from '../useColumn';

  interface Props {
    placeholder?: string;
  }

  withDefaults(defineProps<Props>(), {
    placeholder: '请设置值',
  });

  const slots = defineSlots<{
    prepend?: () => VNode;
    default?: () => VNode;
    append?: () => VNode;
  }>();

  const columnContext = useColumn();

  const modelValue = defineModel<string>();

  const contentRef = useTemplateRef('content');
  const isShowPlacehoder = ref(true);

  watch(modelValue, () => {
    columnContext?.validate('change');
  });

  const calcPlaceholder = () => {
    nextTick(() => {
      isShowPlacehoder.value = !contentRef.value?.innerText;
    });
  };

  const handleBlur = () => {
    columnContext?.blur();
    columnContext?.validate('blur');
  };

  const handleFocus = () => {
    columnContext?.focus();
  };

  onUpdated(() => {
    calcPlaceholder();
  });

  onMounted(() => {
    calcPlaceholder();
  });
</script>
<style lang="less">
  .bk-editable-text {
    position: relative;
    display: flex;
    width: 100%;
    min-height: 40px;
    align-items: center;
    overflow: hidden;
  }

  .bk-editable-text-prepend-wrapper,
  .bk-editable-text-append-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    padding: 0 8px;
    user-select: none;
  }

  .bk-editable-text-prepend-wrapper {
    padding-left: 10px;
  }

  .bk-editable-text-append-wrapper {
    padding-right: 10px;
    margin-left: auto;
  }

  .bk-editable-text-content-wrapper {
    position: relative;
    width: 100%;
    min-height: 40px;
    padding: 10px 0;
    margin: 0 10px;
    overflow: hidden;
    line-height: 20px;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;

    &.is-show-prepend {
      margin-left: 0;
    }

    &.is-show-append {
      margin-right: 0;
    }
  }

  .bk-editable-text-content-placeholder {
    position: absolute;
    display: flex;
    height: 40px;
    overflow: hidden;
    font-size: 12px;
    color: #c4c6cc;
    text-overflow: ellipsis;
    white-space: nowrap;
    user-select: none;
    align-items: center;
    inset: 0;
  }
</style>
