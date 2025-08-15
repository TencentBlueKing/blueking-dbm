<template>
  <div
    class="bk-quick-search-type-mult-cascader"
    :style="{ width: contentMinWidth > 0 ? `${contentMinWidth + 12}px` : '' }">
    <div
      v-if="isSearching && renderSearchList.length > 0"
      key="search"
      class="search-wrapper">
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
      class="list-layout">
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
      v-if="isSearching && renderSearchList.length < 1"
      class="bk-quick-search-type-menu-filter-empty">
      未搜索到 "{{ keyword }}" 相关数据
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { Checkbox } from 'tdesign-vue-next';
  import { ref, useTemplateRef } from 'vue';

  interface Props {
    keyword: string;
    list: {
      children: {
        label: string;
        value: string | number;
      }[];
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

  const layoutRef = useTemplateRef('layout');
  const parentKey = ref<string | number>(props.list[0].value);
  const localValueIdMap = shallowRef<Record<string, IResult>>({});
  const contentMinWidth = ref(0);

  const isSearching = computed(() => Boolean(props.keyword && _.trim(props.keyword)));
  const childrenList = computed(() => _.find(props.list, (item) => item.value === parentKey.value)?.children || []);

  const renderSearchList = computed(() => {
    const keyword = `${props.keyword || ''}`.trim().toLowerCase();
    if (!keyword) {
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
      [] as {
        label: string;
        searchLabel: string;
        value: IResult['value'];
      }[],
    );
  });

  const calcParentCheckStatus = (parentData: Props['list'][number]) => {
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
      const currentValue = modelValue.value[0].value;
      for (const parentItem of props.list) {
        for (const childItem of parentItem.children) {
          if (childItem.value === currentValue) {
            parentKey.value = parentItem.value;
            localValueIdMap.value = modelValue.value.reduce((result, item) => {
              return Object.assign(result, {
                [item.value]: item,
              });
            }, {});
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

  const handleParentChange = (checked: boolean, data: IResult) => {
    const latestValueMap = { ...localValueIdMap.value };
    const childrenList = _.find(props.list, (item) => item.value === data.value)?.children || [];
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
    .list-layout {
      display: flex;
      height: 100%;
      max-height: inherit;
      padding: 8px 0;
      overflow: hidden;
    }

    .parent-wrapper {
      flex: 0 1 auto;
      overflow-y: scroll;
    }

    .children-wrapper {
      overflow-y: scroll;
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
