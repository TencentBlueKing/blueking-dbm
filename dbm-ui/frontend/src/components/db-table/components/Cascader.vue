<template>
  <div
    ref="menuRef"
    class="db-table-filter-type-cascader">
    <div class="t-table__filter-pop-search">
      <Input
        v-model="serachKey"
        autofocus
        borderless
        clearable
        placeholder="请输入关键字">
        <template #prefix-icon> <SearchIcon /></template>
      </Input>
    </div>
    <div
      v-if="isSearch && renderSearchList.length > 0"
      key="search"
      class="search-wrapper">
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
          {{ item.value }}
        </div>
      </div>
    </template>
    <div
      v-if="isSearch && renderSearchList.length < 1"
      class="bk-quick-search-type-menu-filter-empty">
      未搜索到 "{{ keyword }}" 相关数据
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { SearchIcon } from 'tdesign-icons-vue-next';
  import { Input, Radio } from 'tdesign-vue-next';
  import { onMounted, ref } from 'vue';

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

  const serachKey = ref('');
  const parentKey = ref<string | number>('');
  const localValue = ref<string | number>('');

  const isSearch = computed(() => Boolean(props.keyword && _.trim(props.keyword)));
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

  const handleSelectParent = (item: IResult) => {
    parentKey.value = item.value;
  };

  const handleChange = (data: IResult) => {
    localValue.value = data.value;
    modelValue.value = [data];
    emits('change', [data]);
  };

  onMounted(() => {
    handleSelectParent(props.list[0]!);
  });
</script>
<style lang="less">
  .db-table-filter-type-cascader {
    display: flex;
    padding: 8px 0;
    overflow: hidden;

    .search-wrapper {
      flex: 1;
    }

    .parent-wrapper {
      flex: 1;
    }

    .children-wrapper {
      flex: 1;
      border-left: 1px solid #dcdee5;
    }
  }
</style>
