<template>
  <div>
    <div
      ref="root"
      class="bk-quick-search-key-panel">
      <div
        v-for="(dataItem, index) in data"
        :key="index"
        class="key-item"
        :class="{ active: activeIndex === index }"
        @click="handleSelectKey(dataItem)">
        <div>
          {{ dataItem.name }}
        </div>
        <div
          v-if="dataItem.description"
          class="key-description">
          {{ dataItem.description }}
        </div>
      </div>
    </div>
    <div
      key="submitTips"
      class="bk-quick-search-panel-footer">
      <div class="bk-quick-search-panel-submit-tips">
        <div class="action-tips">
          <div class="tag">
            <DbIcon type="up-big" />
          </div>
          <div class="tag">
            <DbIcon type="down-big" />
          </div>
          <span>移动光标</span>
        </div>
        <div class="action-tips">
          <div class="tag">Enter</div>
          <span>选中</span>
        </div>
      </div>
    </div>
  </div>
</template>
<script setup lang="ts">
  import { toRef, useTemplateRef } from 'vue';

  import useMenuKeyboard from '@components/db-quick-search/bk-quick-search/hooks/useMenuKeyboard';
  import type { Props as ContextProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

  interface Props {
    data: ContextProps['data'];
  }

  type Emits = (e: 'change', value: ContextProps['data'][number]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<ContextProps['data'][number]>();

  const keyList = toRef(props, 'data');
  const rootRef = useTemplateRef('root');

  const handleSelectKey = (data: ContextProps['data'][number]) => {
    modelValue.value = data;
    emits('change', data);
  };

  const { activeIndex } = useMenuKeyboard(keyList, rootRef, (value) => {
    handleSelectKey(value);
  });
</script>
<style lang="less">
  .bk-quick-search-key-panel {
    min-width: 230px;
    min-height: 32px;
    padding: 8px 0;
    overflow: hidden auto;
    font-size: 12px;
    pointer-events: all;

    .key-item {
      display: flex;
      height: 32px;
      padding: 0 10px 0 16px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      pointer-events: auto;
      cursor: pointer;
      transition: all 0.1s;
      flex: 1 0 32px;
      align-items: center;
      justify-content: flex-start;

      &:hover {
        color: #3a84ff;
        background-color: #eaf3ff;
      }

      &.active {
        color: #3a84ff;
        background: #f4f6fa;
      }
    }

    .key-description {
      padding-left: 10px;
      margin-left: auto;
      font-size: 12px;
      color: #c4c6cc;
    }
  }
</style>
