<template>
  <div
    ref="menuRef"
    class="db-table-filter-type-mult-cascader"
    :style="{ 'min-width': contentMinWidth > 0 ? `${contentMinWidth}px` : '' }">
    <div class="t-table__filter-pop-search">
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
        </template>
      </div>
    </BkLoading>
    <div
      v-if="isSearch && renderSearchList.length < 1"
      class="t-table-filter-empty">
      <BkException
        :description="t('搜索为空')"
        scene="part"
        type="search-empty" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { SearchIcon } from 'tdesign-icons-vue-next';
  import { Checkbox, Input } from 'tdesign-vue-next';
  import { ref } from 'vue';
  import { useI18n } from 'vue-i18n';

  import useMenuList from './hooks/useMenuList';

  interface IListItem {
    children: {
      label: string;
      value: string | number;
    }[];
    label: string;
    value: string | number;
  }

  export interface Props {
    // 可以选择任意一项
    checkStrictly?: boolean;
    list?: IListItem[];
    // eslint-disable-next-line vue/no-unused-properties
    remoteMethod?: (params: { defaultValue?: string; keyword?: string }) => Promise<IListItem[]>;
    // eslint-disable-next-line vue/no-unused-properties
    remoteSearch?: boolean;
    value?: string;
  }

  type Emits = (e: 'change', value: string) => void;

  const props = withDefaults(defineProps<Props>(), {
    checkStrictly: false,
    list: undefined,
    remoteMethod: undefined,
    remoteSearch: false,
    value: '',
  });

  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const { filterKey, list, loading: isRemoteListLoading } = useMenuList<IListItem>(props);

  const layoutWrapperRef = useTemplateRef('layoutWrapper');
  const contentMinWidth = ref(0);
  const expanedParent = ref<IListItem>();
  const localValueIdMap = shallowRef<Record<string, IListItem['value']>>({});

  const isSearch = computed(() => Boolean(filterKey.value && _.trim(filterKey.value)));
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
      [] as ({
        searchLabel: string;
      } & IListItem['children'][number])[],
    );
  });

  const calcParentCheckStatus = (parentData: IListItem) => {
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
      contentMinWidth.value = Math.max(layoutWrapperRef.value!.getBoundingClientRect().width, contentMinWidth.value);
    });
  };

  let isInnerSelfChange = false;
  watch(
    () => props.value,
    () => {
      if (isInnerSelfChange) {
        isInnerSelfChange = false;
        return;
      }
      if (!props.value) {
        localValueIdMap.value = {};
        return;
      }
      localValueIdMap.value = props.value.split(',').reduce((result, item) => {
        return Object.assign(result, {
          [item]: item,
        });
      }, {});
    },
    {
      immediate: true,
    },
  );

  const handleExpaneParent = (item: IListItem) => {
    expanedParent.value = item;
    calcPanelWidth();
  };

  watch(
    list,
    () => {
      if (list.value.length < 1) {
        return;
      }

      if (!props.value) {
        handleExpaneParent(list.value[0]);
      } else {
        const currentValue = props.value.split(',')[0];
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
  const triggerChange = () => {
    isInnerSelfChange = true;
    emits('change', Object.values(localValueIdMap.value).join(','));
  };

  const handleParentChange = (checked: boolean, data: IListItem) => {
    const latestValueMap = { ...localValueIdMap.value };
    if (props.checkStrictly) {
      // 父级可以作为值被选中
      if (checked) {
        latestValueMap[data.value] = data.value;
      } else {
        delete latestValueMap[data.value];
      }
    } else {
      data.children.forEach((item) => {
        if (checked) {
          latestValueMap[item.value] = item.value;
        } else {
          delete latestValueMap[item.value];
        }
      });
    }
    localValueIdMap.value = latestValueMap;
    triggerChange();
  };

  const handleChange = (data: IListItem['children'][number]) => {
    const latestValueMap = { ...localValueIdMap.value };

    if (localValueIdMap.value[data.value]) {
      delete latestValueMap[data.value];
    } else {
      latestValueMap[data.value] = data.value;
    }
    localValueIdMap.value = latestValueMap;

    triggerChange();
  };

  onMounted(() => {
    calcPanelWidth();
  });
</script>
<style lang="less">
  .db-table-filter-type-mult-cascader {
    .layout-wrapper {
      display: flex;
      max-height: 280px;
      margin-top: 8px;
      margin-bottom: 8px;
      overflow: hidden;
    }

    .parent-wrapper {
      flex: 0 1 auto;
      overflow-y: auto;
    }

    .children-wrapper {
      flex: 1;
      overflow-y: auto;
      border-left: 1px solid #dcdee5;
    }

    .search-wrapper {
      flex: 1;
      overflow-y: auto;
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
