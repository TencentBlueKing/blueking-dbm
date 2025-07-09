<template>
  <div
    ref="menuRef"
    class="bk-quick-search-key-menu">
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
</template>
<script setup lang="ts">
  import { ref, toRef } from 'vue';

  import type { Props as ContextProps } from '@components/db-quick-serach/bk-quick-search/Index.vue';

  import useMenuKeyboard from '@/components/db-quick-serach/bk-quick-search/hooks/useMenuKeyboard';

  interface Props {
    data: ContextProps['data'];
  }

  type Emits = (e: 'change', value: ContextProps['data'][number]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<ContextProps['data'][number]>();

  const keyList = toRef(props, 'data');
  const menuRef = ref();

  const handleSelectKey = (data: ContextProps['data'][number]) => {
    modelValue.value = data;
    emits('change', data);
  };

  const { activeIndex } = useMenuKeyboard(keyList, menuRef, (value) => {
    handleSelectKey(value);
  });
</script>
<style lang="less">
  .bk-quick-search-key-menu {
    min-width: 230px;
    min-height: 32px;
    padding: 8px 0;
    margin: -5px -9px;
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
