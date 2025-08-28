<template>
  <div
    ref="root"
    class="bk-quick-search-type-select">
    <div class="bk-quick-search-type-menu-filter-box">
      <Input
        v-model="serachKey"
        borderless
        clearable
        placeholder="请输入关键字">
        <template #prefix-icon> <SearchIcon /></template>
      </Input>
    </div>
    <div
      ref="layout"
      class="bk-quick-search-value-wrapper">
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
      v-if="serachKey && renderList.length < 1"
      class="bk-quick-search-type-menu-filter-empty">
      未搜索到 "{{ serachKey }}" 相关数据
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { SearchIcon } from 'tdesign-icons-vue-next';
  import { Input, Radio } from 'tdesign-vue-next';
  import { ref, useTemplateRef } from 'vue';

  import useMenuKeyboard from '@/components/db-quick-serach/bk-quick-search/hooks/useMenuKeyboard';

  interface Props {
    list: {
      label: string;
      value: string | number;
    }[];
    remoteSearch: boolean;
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
  const serachKey = ref('');

  const renderList = computed(() => {
    const keyword = `${serachKey.value || ''}`.trim().toLowerCase();
    if (!keyword || props.remoteSearch) {
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

      localValue.value = modelValue.value[0]!.value;
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
    padding: 8px 12px;
  }
</style>
