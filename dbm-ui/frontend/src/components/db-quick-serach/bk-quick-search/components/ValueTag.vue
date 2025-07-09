<template>
  <div
    class="bk-quick-search-value-tag"
    :class="{
      'is-removeable': isShowRemoveBtn && !slots.edit,
      'is-focused': focued,
    }"
    :style="tagStyles">
    <div
      class="bk-quick-search-value-tag-layout"
      @click="handleClick">
      <div class="bk-quick-search-value-tag-label"><slot />:</div>
      <div
        v-if="slots.value"
        class="bk-quick-search-value-tag-value">
        <div
          class="bk-quick-search-value-tag-text"
          :style="tagTextStyles">
          <slot name="value" />
        </div>
      </div>
      <slot
        v-if="slots.edit"
        name="edit" />
    </div>
    <div
      v-if="slots.value && removeable"
      class="bk-quick-search-value-tag-remote-btn"
      @click="handleRemove">
      <Icon name="close" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { Icon } from 'tdesign-vue-next';
  import { computed, inject, type StyleValue, type VNode } from 'vue';

  import { BK_QUICK_SEARCH } from '@components/db-quick-serach/bk-quick-search/Index.vue';

  interface Props {
    focued?: boolean;
    removeable?: boolean;
  }

  interface Slots {
    default: () => VNode;
    edit?: () => VNode;
    value?: () => VNode;
  }

  interface Emits {
    (e: 'remove'): void;
    (e: 'edit'): void;
  }

  const props = withDefaults(defineProps<Props>(), {
    removeable: true,
  });

  const emits = defineEmits<Emits>();

  const slots = defineSlots<Slots>();

  const context = inject(BK_QUICK_SEARCH);

  const tagStyles = computed<StyleValue>(() => {
    if (context!.isFouced || !props.removeable) {
      return {
        height: 'auto',
      };
    }
    return {
      height: '22px',
    };
  });

  const isShowRemoveBtn = computed(() => props.removeable && slots.value);

  const tagTextStyles = computed<StyleValue>(() => {
    if (context!.isFouced || !props.removeable) {
      return {
        'word-break': 'break-all',
      };
    }

    // 失焦时，限制 tag 在一行展示
    return {
      overflow: 'hidden',
      'text-overflow': 'ellipsis',
      'white-space': 'nowrap',
    };
  });

  const handleClick = () => {
    emits('edit');
  };

  const handleRemove = () => {
    emits('remove');
  };
</script>
<style lang="less">
  .bk-quick-search {
    &.is-focused {
      .bk-quick-search-value-tag-text {
        max-width: unset !important;
      }
    }
  }

  .bk-quick-search-value-tag {
    position: relative;
    display: inline-flex;
    max-width: 100%;
    padding: 0 8px;
    margin-top: 4px;
    margin-right: 4px;
    overflow: hidden;
    font-size: 12px;
    line-height: 22px;
    color: #63656e;
    cursor: pointer;
    background: #f0f1f5;
    border-radius: 2px;
    flex: 0 0 auto;

    &:hover {
      background: #dcdee5;
    }

    &.is-focused {
      height: auto;
      background-color: #fff;

      &.is-custom-input,
      &.is-single-input {
        flex: 0 0 100%;

        .bk-quick-search-value-tag-layout {
          flex: 1;
        }
      }
    }

    &.is-removeable {
      padding-right: 22px;
    }
  }

  .bk-quick-search-value-tag-layout {
    display: flex;
    align-items: flex-start;
    overflow: hidden;
  }

  .bk-quick-search-value-tag-label {
    padding-right: 4px;
    word-break: keep-all;
    flex: 0 1 auto;
    white-space: pre;
  }

  .bk-quick-search-value-tag-value {
    display: flex;
    overflow: hidden;
    user-select: none;
  }

  .bk-quick-search-value-tag-remote-btn {
    position: absolute;
    top: 0;
    right: 0;
    display: flex;
    width: 22px;
    align-items: center;
    justify-content: center;
    height: 22px;
  }
</style>
