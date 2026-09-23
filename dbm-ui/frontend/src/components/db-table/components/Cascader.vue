<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at https://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <div class="db-table-filter-type-cascader">
    <div class="t-table__filter-pop-search">
      <Input
        v-model="searchKey"
        autofocus
        borderless
        clearable
        :placeholder="t('请输入关键字')">
        <template #prefix-icon> <SearchIcon /></template>
      </Input>
    </div>
    <div class="layout-wrapper">
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
            {{ item.label }}
          </div>
        </div>
      </template>
    </div>
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
  import { Input, Radio } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  interface Props {
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

  const { t } = useI18n();

  const searchKey = ref('');
  const parentKey = ref<string | number>('');
  const localValue = ref<string | number>('');

  const isSearch = computed(() => Boolean(_.trim(searchKey.value)));
  const childrenList = computed(() => _.find(props.list, (item) => item.value === parentKey.value)?.children || []);

  const renderSearchList = computed(() => {
    const keyword = searchKey.value.trim().toLowerCase();
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
    // 已选值所在的父级已由 modelValue 定位，没有选中值时才默认展开第一项
    if (!parentKey.value && props.list.length > 0) {
      handleSelectParent(props.list[0]);
    }
  });
</script>
<style lang="less">
  .db-table-filter-type-cascader {
    padding-bottom: 8px;

    .layout-wrapper {
      display: flex;
      margin-top: 8px;
      overflow: hidden;
    }

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

    .value-item {
      display: flex;
      height: 32px;
      padding: 0 10px 0 16px;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      cursor: pointer;
      align-items: center;

      &:hover {
        color: #3a84ff;
        background-color: #eaf3ff;
      }

      &.active {
        color: #3a84ff;
        background: #f4f6fa;
      }
    }
  }
</style>
