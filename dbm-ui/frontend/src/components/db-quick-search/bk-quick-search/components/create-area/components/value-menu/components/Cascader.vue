<template>
  <div
    class="bk-quick-search-type-cascader"
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
        v-if="isSearching"
        key="search"
        ref="layout"
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

  import type { Props as ContextProps } from '@components/db-quick-search/bk-quick-search/Index.vue';

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

  const {
    filterKey,
    list,
    loading: isRemoteListLoading,
  } = useMenuList<{ children: IResult[] } & IResult>(props.config);

  const layoutRef = useTemplateRef('layout');
  const contentMinWidth = ref(0);
  const parentKey = ref<string | number>('');
  const localValue = ref<string | number>('');

  const isSearching = computed(() => Boolean(filterKey.value && _.trim(filterKey.value)));
  const childrenList = computed(() => _.find(list.value, (item) => item.value === parentKey.value)?.children || []);

  const renderSearchList = computed(() => {
    const keyword = `${filterKey.value || ''}`.trim().toLowerCase();
    if (!keyword) {
      return [];
    }

    return list.value.reduce(
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
      for (const parentItem of list.value) {
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
    list,
    () => {
      if (list.value.length < 1) {
        return;
      }

      handleSelectParent(list.value[0]!);
      setTimeout(() => {
        contentMinWidth.value = Math.max(layoutRef.value!.getBoundingClientRect().width, contentMinWidth.value);
      });
    },
    {
      immediate: true,
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
  });
</script>
<style lang="less">
  .bk-quick-search-type-cascader {
    padding-bottom: 8px;

    .bk-quick-search-value-wrapper {
      display: flex;
      min-width: max-content;
      overflow: unset;
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
      flex: 1 0 auto;
    }
  }
</style>
