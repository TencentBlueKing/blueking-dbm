<template>
  <div
    ref="root"
    class="bk-quick-search-type-select">
    <div ref="layout">
      <div
        v-for="(valueItem, index) in renderList"
        :key="valueItem.value"
        class="value-item"
        :class="{ active: activeIndex === index }"
        @click="handleChange(valueItem)">
        <Radio
          :checked="valueItem.value === localValue"
          style="pointer-events: none" />
        {{ valueItem.label }}
      </div>
    </div>
    <div
      v-if="keyword && renderList.length < 1"
      class="bk-quick-search-type-menu-filter-empty">
      未搜索到 "{{ keyword }}" 相关数据
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { Radio } from 'tdesign-vue-next';
  import { ref, useTemplateRef } from 'vue';

  import useMenuKeyboard from '@/components/db-quick-serach/bk-quick-search/hooks/useMenuKeyboard';

  interface Props {
    keyword: string;
    list: {
      label: string;
      value: string | number;
    }[];
  }

  interface IResult {
    label: string;
    value: string | number;
  }

  type Emits = (e: 'change', value: IResult[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<IResult[]>({
    default: () => [],
  });

  const rootRef = useTemplateRef<HTMLElement>('root');
  const layoutRef = useTemplateRef('layout');
  const contentMinWidth = ref(0);
  const localValue = ref<string | number>('');

  const renderList = computed(() => {
    const keyword = `${props.keyword || ''}`.trim().toLowerCase();
    if (!keyword) {
      return props.list;
    }

    return _.filter(props.list, (item) => item.label.toLowerCase().includes(keyword));
  });

  watch(
    modelValue,
    () => {
      if (modelValue.value.length < 1) {
        return;
      }

      localValue.value = modelValue.value[0].value;
    },
    {
      immediate: true,
    },
  );

  watch(
    () => props.list,
    () => {
      nextTick(() => {
        contentMinWidth.value = Math.max(layoutRef.value!.getBoundingClientRect().width, contentMinWidth.value);
      });
    },
  );

  const handleChange = (data: IResult) => {
    localValue.value = data.value;
    emits('change', [data]);
  };

  const { activeIndex } = useMenuKeyboard(renderList, rootRef, (value) => {
    handleChange(value);
  });

  onMounted(() => {
    contentMinWidth.value = layoutRef.value!.getBoundingClientRect().width;
  });
</script>
<style lang="less">
  .bk-quick-search-type-select {
    padding: 8px 0;
  }
</style>
