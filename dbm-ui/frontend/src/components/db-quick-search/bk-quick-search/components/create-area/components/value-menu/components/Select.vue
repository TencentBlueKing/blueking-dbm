<template>
  <div
    class="bk-quick-search-type-select"
    :style="{ width: contentMinWidth > 0 ? `${contentMinWidth}px` : '' }">
    <div class="bk-quick-search-value-panel-filter-box">
      <Input
        v-model="filterKey"
        autofocus
        borderless
        clearable
        placeholder="请输入关键字">
        <template #prefix-icon> <SearchIcon /></template>
      </Input>
    </div>
    <BkLoading :loading="isRemoteListLoading">
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
        v-if="filterKey && renderList.length < 1"
        class="bk-quick-search-value-panel-filter-empty">
        <BkException
          description="搜索为空"
          scene="part"
          type="search-empty" />
      </div>
    </BkLoading>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { SearchIcon } from 'tdesign-icons-vue-next';
  import { Input, Radio } from 'tdesign-vue-next';
  import { onMounted, ref, useTemplateRef } from 'vue';

  import useMenuKeyboard from '@components/db-quick-search/bk-quick-search/hooks/useMenuKeyboard';
  import type { Props as ContextProps } from '@components/db-quick-search/bk-quick-search/Index.vue';
  import { makeMap } from '@components/db-quick-search/bk-quick-search/utils';

  import useMenuList from '../hooks/useMenuList';

  interface Props {
    config: ContextProps['data'][number];
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

  const defaultModelValue = [...modelValue.value];

  const { filterKey, list, loading: isRemoteListLoading } = useMenuList<IResult>(props.config);

  const layoutRef = useTemplateRef('layout');
  const contentMinWidth = ref(0);
  const localValue = ref<string | number>('');

  const renderList = computed(() => {
    const keyword = filterKey.value.trim().toLowerCase();
    if (!keyword) {
      const modelValueMap = makeMap(defaultModelValue.map((item) => item.value));
      return [...defaultModelValue, ..._.filter(list.value, (item) => !modelValueMap[item.value])];
    }

    return _.filter(list.value, (item) => item.label.toLowerCase().includes(keyword));
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

  watch(list, () => {
    if (list.value.length < 1) {
      return;
    }
    nextTick(() => {
      contentMinWidth.value = Math.max(layoutRef.value!.getBoundingClientRect().width, contentMinWidth.value);
    });
  });

  const handleChange = (data: IResult) => {
    localValue.value = data.value;
    emits('change', [data]);
  };

  const { activeIndex } = useMenuKeyboard(renderList, layoutRef, (value) => {
    handleChange(value);
  });

  onMounted(() => {
    contentMinWidth.value = layoutRef.value!.getBoundingClientRect().width;
  });
</script>
<style lang="less">
  .bk-quick-search-type-select {
    padding-bottom: 8px;
  }
</style>
