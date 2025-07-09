<template>
  <div
    class="bk-quick-search-type-mult-cascader"
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
          <Checkbox
            :checked="Boolean(localValueIdMap[item.value])"
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
            <Checkbox
              v-bind="calcParentCheckStatus(item)"
              @change="(value) => handleParentChange(value, item)" />
            {{ item.label }}
          </div>
        </div>
        <div
          :key="parentKey"
          class="children-wrapper">
          <div
            v-for="item in childrenList"
            :key="item.value"
            class="value-item"
            @click="() => handleChange(item)">
            <Checkbox
              :checked="Boolean(localValueIdMap[item.value])"
              style="pointer-events: none" />
            {{ item.label }}
          </div>
        </div>
      </div>
      <div
        v-if="isSearching && renderSearchList.length < 1 && !isRemoteListLoading"
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
  import { Checkbox, Input } from 'tdesign-vue-next';
  import { ref, useTemplateRef } from 'vue';

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
  const parentKey = ref<string | number>('');
  const localValueIdMap = shallowRef<Record<string, IResult>>({});
  const contentMinWidth = ref(0);

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
      [] as {
        label: string;
        searchLabel: string;
        value: IResult['value'];
      }[],
    );
  });

  const calcParentCheckStatus = (parentData: { children: IResult[] } & IResult) => {
    let indeterminate = false;
    let checked = true;
    parentData.children.forEach((item) => {
      if (!localValueIdMap.value[item.value]) {
        checked = false;
      }
      if (localValueIdMap.value[item.value]) {
        indeterminate = true;
      }
    });
    return {
      checked,
      indeterminate: checked ? false : indeterminate,
    };
  };

  const calcPanelWidth = () => {
    setTimeout(() => {
      contentMinWidth.value = Math.max(layoutRef.value!.getBoundingClientRect().width, contentMinWidth.value);
    });
  };

  let isInnerSelfChange = false;
  watch(
    modelValue,
    () => {
      if (isInnerSelfChange) {
        isInnerSelfChange = false;
        return;
      }
      if (modelValue.value.length < 1) {
        localValueIdMap.value = {};
        return;
      }
      localValueIdMap.value = modelValue.value.reduce((result, item) => {
        return Object.assign(result, {
          [item.value]: item,
        });
      }, {});
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

      if (modelValue.value.length < 1) {
        parentKey.value = list.value[0]!.value;
      } else {
        const currentValue = modelValue.value[0]!.value;
        for (const parentItem of list.value) {
          for (const childItem of parentItem.children) {
            if (childItem.value === currentValue) {
              parentKey.value = parentItem.value;
              break;
            }
          }
        }
      }
      calcPanelWidth();
    },
    {
      immediate: true,
    },
  );

  const handleSelectParent = (item: IResult) => {
    parentKey.value = item.value;
    calcPanelWidth();
  };

  const handleParentChange = (checked: boolean, data: IResult) => {
    const latestValueMap = { ...localValueIdMap.value };
    const childrenList = _.find(list.value, (item) => item.value === data.value)?.children || [];
    childrenList.forEach((item) => {
      if (checked) {
        latestValueMap[item.value] = item;
      } else {
        delete latestValueMap[item.value];
      }
    });
    localValueIdMap.value = latestValueMap;

    isInnerSelfChange = true;
    emits('change', Object.values(latestValueMap));
  };

  const handleChange = (data: IResult) => {
    const latestValueMap = { ...localValueIdMap.value };

    if (localValueIdMap.value[data.value]) {
      delete latestValueMap[data.value];
    } else {
      latestValueMap[data.value] = data;
    }
    localValueIdMap.value = latestValueMap;

    isInnerSelfChange = true;
    emits('change', Object.values(latestValueMap));
  };

  onMounted(() => {
    contentMinWidth.value = layoutRef.value!.getBoundingClientRect().width;
  });
</script>
<style lang="less">
  .bk-quick-search-type-mult-cascader {
    padding-bottom: 8px;

    .bk-quick-search-value-wrapper {
      display: flex;
      min-width: max-content;
      overflow: unset;
    }

    .filter-result-list {
      flex-direction: column;
      overflow-y: auto;
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

    .item-checkbox {
      width: 16px;
      height: 16px;
      margin-right: 8px;
      border: 1px solid #979ba5;
      border-radius: 2px;
      transition: all 0.1s;

      &.is-checked {
        position: relative;
        background: #3a84ff;
        border-color: #3a84ff;

        &::after {
          position: absolute;
          top: 4px;
          left: 3px;
          width: 6px;
          height: 3px;
          border: 2px solid #fff;
          border-top: none;
          border-right: none;
          content: '';
          transform: rotateZ(-45deg);
        }
      }
    }
  }
</style>
