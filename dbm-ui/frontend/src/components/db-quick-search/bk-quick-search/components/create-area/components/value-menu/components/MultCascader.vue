<template>
  <div
    class="bk-quick-search-type-mult-cascader"
    :style="{ 'min-width': contentMinWidth > 0 ? `${contentMinWidth}px` : '' }">
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
            :class="{ active: item.value === expanedParent?.value }"
            @click="() => handleExpaneParent(item)">
            <Checkbox
              v-bind="calcParentCheckStatus(item)"
              @change="(value) => handleParentChange(value, item)" />
            {{ item.label }}
          </div>
        </div>
        <div
          :key="expanedParent?.value"
          class="children-wrapper">
          <div
            v-for="item in expanedParent?.children"
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
    // 可以选择任意一项
    checkStrictly?: boolean;
    config: ContextProps['data'][number];
    // showAllLevels——是否显示选中项的完整路径（控制值回显的效果）
    showAllLevels?: boolean;
  }

  interface IResult {
    label: string;
    value: string | number;
  }

  type IListItem = { children: IResult[] } & IResult;

  type Emits = (e: 'change', value: IResult[]) => void;

  const props = withDefaults(defineProps<Props>(), {
    checkStrictly: false,
    showAllLevels: false,
  });

  const emits = defineEmits<Emits>();

  const modelValue = defineModel<IResult[]>({
    default: () => [],
  });

  const { filterKey, list, loading: isRemoteListLoading } = useMenuList<IListItem>(props.config);

  const layoutRef = useTemplateRef('layout');
  const expanedParent = ref<IListItem>();
  const localValueIdMap = shallowRef<Record<string, IResult>>({});
  const contentMinWidth = ref(0);

  const isSearching = computed(() => Boolean(filterKey.value && _.trim(filterKey.value)));

  const renderSearchList = computed(() => {
    const keyword = `${filterKey.value || ''}`.trim().toLowerCase();
    if (!keyword) {
      return [];
    }

    return list.value.reduce(
      (result, parentItem) => {
        if (props.checkStrictly && parentItem.label.toLowerCase().includes(keyword)) {
          result.push({
            label: parentItem.label,
            searchLabel: parentItem.label,
            value: parentItem.value,
          });
        }
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
    if (props.checkStrictly) {
      return {
        checked: Boolean(localValueIdMap.value[parentData.value]),
        indeterminate: false,
      };
    }
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

  const getResultValue = (data: IResult) => ({
    label: props.showAllLevels ? `${expanedParent.value?.label}/${data.label}` : data.label,
    value: data.value,
  });

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
        handleExpaneParent(list.value[0]);
      } else {
        const currentValue = modelValue.value[0]!.value;
        for (const parentItem of list.value) {
          if (props.checkStrictly && parentItem.value === currentValue) {
            handleExpaneParent(parentItem);
            break;
          }
          for (const childItem of parentItem.children) {
            if (childItem.value === currentValue) {
              handleExpaneParent(parentItem);
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

  const handleExpaneParent = (item: IListItem) => {
    expanedParent.value = item;
    calcPanelWidth();
  };

  const handleParentChange = (checked: boolean, data: IListItem) => {
    const latestValueMap = { ...localValueIdMap.value };

    if (props.checkStrictly) {
      // 父级可以作为值被选中
      if (checked) {
        latestValueMap[data.value] = {
          label: data.label,
          value: data.value,
        };
      } else {
        delete latestValueMap[data.value];
      }
    } else {
      // 只能选择叶子节点
      data.children.forEach((item) => {
        if (checked) {
          latestValueMap[item.value] = getResultValue(item);
        } else {
          delete latestValueMap[item.value];
        }
      });
    }

    localValueIdMap.value = latestValueMap;

    isInnerSelfChange = true;
    emits('change', Object.values(latestValueMap));
  };

  const handleChange = (data: IResult) => {
    const latestValueMap = { ...localValueIdMap.value };

    if (localValueIdMap.value[data.value]) {
      delete latestValueMap[data.value];
    } else {
      latestValueMap[data.value] = getResultValue(data);
    }
    localValueIdMap.value = latestValueMap;

    isInnerSelfChange = true;
    emits('change', Object.values(latestValueMap));
  };

  onMounted(() => {
    calcPanelWidth();
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
