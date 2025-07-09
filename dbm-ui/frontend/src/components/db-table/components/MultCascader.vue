<template>
  <div
    ref="menuRef"
    class="db-table-filter-type-mult-cascader"
    :style="{ width: contentMinWidth > 0 ? `${contentMinWidth + 12}px` : '' }">
    <div class="t-table__filter-pop-search">
      <Input
        v-model="serachKey"
        borderless
        clearable
        placeholder="请输入关键字">
        <template #prefix-icon> <SearchIcon /></template>
      </Input>
    </div>
    <div
      ref="layoutWrapper"
      class="layout-wrapper">
      <div
        v-if="isSearch && renderSearchList.length > 0"
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
      <template v-if="!isSearch">
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
      </template>
    </div>
    <div
      v-if="isSearch && renderSearchList.length < 1"
      class="bk-quick-search-type-menu-filter-empty">
      未搜索到 "{{ serachKey }}" 相关数据
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { SearchIcon } from 'tdesign-icons-vue-next';
  import { Checkbox, Input } from 'tdesign-vue-next';
  import { ref } from 'vue';

  export type IResult = string | number;

  export interface Props {
    list: {
      children: {
        label: string;
        value: string | number;
      }[];
      label: string;
      value: string | number;
    }[];
    value?: IResult[];
  }

  type Emits = (e: 'change', value: IResult[]) => void;

  const props = defineProps<Props>();

  const emits = defineEmits<Emits>();

  const layoutWrapperRef = useTemplateRef('layoutWrapper');
  const contentMinWidth = ref(0);

  const serachKey = ref('');
  const parentKey = ref<string | number>(props.list[0].value);
  const localValueIdMap = shallowRef<Record<string, IResult>>({});

  const isSearch = computed(() => Boolean(serachKey.value && _.trim(serachKey.value)));
  const childrenList = computed(() => _.find(props.list, (item) => item.value === parentKey.value)?.children || []);

  const renderSearchList = computed(() => {
    const keyword = `${serachKey.value || ''}`.trim().toLowerCase();
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
        value: IResult;
      }[],
    );
  });

  let isInnerSelfChange = false;
  watch(
    () => props.value,
    () => {
      if (isInnerSelfChange) {
        isInnerSelfChange = false;
        return;
      }
      if (!props.value || props.value.length < 1) {
        localValueIdMap.value = {};
        return;
      }
      const currentValue = props.value[0];
      for (const parentItem of props.list) {
        for (const childItem of parentItem.children) {
          if (childItem.value === currentValue) {
            parentKey.value = parentItem.value;
            localValueIdMap.value = props.value.reduce((result, item) => {
              return Object.assign(result, {
                [item]: item,
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
        contentMinWidth.value = Math.max(layoutWrapperRef.value!.getBoundingClientRect().width, contentMinWidth.value);
      });
    },
  );

  const handleSelectParent = (item: Props['list'][number]) => {
    parentKey.value = item.value;
  };

  const handleChange = (data: Props['list'][number]['children'][number]) => {
    const latestValueMap = { ...localValueIdMap.value };

    if (localValueIdMap.value[data.value]) {
      delete latestValueMap[data.value];
    } else {
      latestValueMap[data.value] = data.value;
    }
    localValueIdMap.value = latestValueMap;

    isInnerSelfChange = true;
    emits('change', Object.values(latestValueMap));
  };

  onMounted(() => {
    contentMinWidth.value = layoutWrapperRef.value!.getBoundingClientRect().width;
  });
</script>
<style lang="less">
  .db-table-filter-type-mult-cascader {
    .layout-wrapper {
      display: flex;
      max-height: 450px;
      margin-top: 8px;
      overflow: hidden;
    }

    .parent-wrapper {
      flex: 1;
      overflow-y: auto;
    }

    .children-wrapper {
      flex: 1;
      overflow-y: auto;
      border-left: 1px solid #dcdee5;
    }

    .search-wrapper {
      flex: 1;
    }

    .value-item {
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
