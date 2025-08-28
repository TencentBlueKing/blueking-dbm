<template>
  <div class="bk-quick-search-type-cascader">
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
      v-if="isSearching && renderSearchList.length > 0"
      key="search"
      class="bk-quick-search-value-wrapper filter-result-list">
      <div
        v-for="(item, index) in renderSearchList"
        :key="index"
        class="value-item"
        @click="() => handleChange(item)">
        <Radio
          :checked="item.value === localValue"
          style="pointer-events: none" />
        {{ item.searchLabel }}
      </div>
    </div>
    <div
      v-if="!isSearching"
      ref="layout"
      class="bk-quick-search-value-wrapper">
      <div class="parent-wrapper">
        <div
          v-for="item in list"
          :key="item.value"
          class="value-item"
          :class="{ active: item.value === parentKey }"
          @click="() => handleSelectParent(item)">
          {{ item.label }}
        </div>
      </div>
      <div class="children-wrapper">
        <div
          v-for="item in childrenList"
          :key="item.value"
          class="value-item"
          :class="{ active: item.value === localValue }"
          @click="() => handleChange(item)">
          <Radio
            :checked="item.value === localValue"
            style="pointer-events: none" />
          {{ item.label }}
        </div>
      </div>
    </div>
    <div
      v-if="isSearching && renderSearchList.length < 1"
      class="bk-quick-search-type-menu-filter-empty">
      未搜索到 "{{ serachKey }}" 相关数据
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { SearchIcon } from 'tdesign-icons-vue-next';
  import { Input, Radio } from 'tdesign-vue-next';
  import { onMounted, ref, useTemplateRef } from 'vue';

  interface Props {
    list: {
      children: {
        label: string;
        value: string | number;
      }[];
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

  const layoutRef = useTemplateRef('layout');
  const contentMinWidth = ref(0);
  const serachKey = ref('');
  const parentKey = ref<string | number>('');
  const localValue = ref<string | number>('');

  const isSearching = computed(() => Boolean(serachKey.value && _.trim(serachKey.value)));
  const childrenList = computed(() => _.find(props.list, (item) => item.value === parentKey.value)?.children || []);

  const renderSearchList = computed(() => {
    const keyword = `${serachKey.value || ''}`.trim().toLowerCase();
    if (!keyword || props.remoteSearch) {
      return [];
    }

    return props.list.reduce(
      (result, parentItem) => {
        parentItem.children.forEach((childItem) => {
          if (childItem.label.toLowerCase().includes(keyword)) {
            result.push({
              ...childItem,
              searchLabel: `${parentItem.label} / ${childItem.label}`,
            });
          }
        });
        return result;
      },
      [] as { label: string; searchLabel: string; value: string | number }[],
    );
  });

  watch(
    modelValue,
    () => {
      if (modelValue.value.length < 1) {
        return;
      }
      const currentValue = modelValue.value[0]!.value;
      for (const parentItem of props.list) {
        for (const childItem of parentItem.children) {
          if (childItem.value === currentValue) {
            parentKey.value = parentItem.value;
            localValue.value = currentValue;
            return;
          }
        }
      }
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

  const handleSelectParent = (item: IResult) => {
    parentKey.value = item.value;
  };

  const handleChange = (data: IResult) => {
    localValue.value = data.value;
    modelValue.value = [data];
    emits('change', [data]);
  };

  onMounted(() => {
    contentMinWidth.value = layoutRef.value!.getBoundingClientRect().width;
    handleSelectParent(props.list[0]!);
  });
</script>
<style lang="less">
  .bk-quick-search-type-cascader {
    padding: 8px 12px;

    .bk-quick-search-value-wrapper {
      display: flex;
      padding: 8px 0;
      overflow: hidden;
    }

    .filter-result-list {
      overflow-y: auto;
      flex-direction: column;
    }

    .parent-wrapper {
      min-width: 120px;
      overflow-y: auto;
      flex: 0 1 auto;
    }

    .children-wrapper {
      min-width: 120px;
      overflow-y: auto;
      border-left: 1px solid #dcdee5;
      flex: 1;
    }
  }
</style>
