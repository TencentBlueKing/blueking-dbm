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
  <div :style="{ width: contentMinWidth > 0 ? `${contentMinWidth}px` : '' }">
    <div
      ref="searchBox"
      class="t-table__filter-pop-search">
      <Input
        v-model="filterKey"
        borderless
        clearable
        :placeholder="t('请输入关键字')">
        <template #prefix-icon> <SearchIcon /></template>
      </Input>
    </div>
    <BkLoading :loading="isRemoteListLoading">
      <div
        ref="wrapper"
        class="t-table__filter-pop-wrapper">
        <CheckboxGroup
          v-model="localValue"
          @change="handleChange">
          <div
            v-for="item in renderList"
            :key="item.value"
            class="t-table__filter-pop-item"
            :class="{ 'empty-item': renderList.length >= 2 && item.value === SpecialOptions.EMPTY }">
            <Checkbox
              :label="item.label"
              style="display: flex; flex: 1; flex-wrap: nowrap; white-space: nowrap"
              :value="item.value" />
          </div>
        </CheckboxGroup>
      </div>
    </BkLoading>
    <div
      v-if="filterKey && renderList.length < 1 && !isRemoteListLoading"
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
  import { Checkbox, CheckboxGroup, type CheckboxGroupValue, Input } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import { SpecialOptions } from '@common/const';

  import { makeMap } from '@utils';

  import useMenuList from './hooks/useMenuList';

  export interface Props {
    // eslint-disable-next-line vue/no-unused-properties
    list?: {
      label: string;
      value: number | string;
    }[];
    remoteMethod?: (params: {
      defaultValue?: string;
      keyword?: string;
    }) => Promise<{ label: string; value: number | string }[]>;
    remoteSearch?: boolean;
    value?: string;
  }

  type Emits = (e: 'change', value: string) => void;

  defineOptions({
    inheritAttrs: false,
  });

  const props = withDefaults(defineProps<Props>(), {
    list: () => [],
    remoteMethod: undefined,
    remoteSearch: false,
    value: '',
  });
  const emits = defineEmits<Emits>();

  const { t } = useI18n();
  const {
    filterKey,
    list,
    loading: isRemoteListLoading,
  } = useMenuList<{ label: string; value: number | string }>(props);

  const defaultValue = shallowRef<{ label: string; value: number | string }[]>([]);

  const wrapperRef = useTemplateRef('wrapper');
  const localValue = shallowRef(props.value ? props.value.split(',') : []);
  const searchBoxRef = useTemplateRef('searchBox');
  const contentMinWidth = ref(0);

  const renderList = computed(() => {
    const keyword = `${filterKey.value || ''}`.trim().toLowerCase();
    // 无关键字时已选项置顶，远程搜索的首屏结果里不一定包含已选项
    if (!keyword) {
      const modelValueMap = makeMap(defaultValue.value.map((item) => item.value));
      return [...defaultValue.value, ..._.filter(list.value, (item) => !modelValueMap[item.value])];
    }
    // 远程搜索的结果已按关键字过滤
    if (props.remoteSearch) {
      return list.value;
    }

    return _.filter(list.value, (item) => item.label.toLowerCase().includes(keyword));
  });

  watch(filterKey, () => {
    nextTick(() => {
      contentMinWidth.value = Math.max(wrapperRef.value!.getBoundingClientRect().width, contentMinWidth.value);
    });
  });

  watch(
    () => props.value,
    () => {
      if (defaultValue.value.length > 0) {
        return;
      }
      if (props.value && _.isFunction(props.remoteMethod)) {
        props.remoteMethod!({
          defaultValue: props.value,
        }).then((data) => {
          defaultValue.value = data;
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: CheckboxGroupValue) => {
    emits('change', value.join(','));
  };

  onMounted(() => {
    setTimeout(() => {
      searchBoxRef.value?.querySelector('input')?.focus();
    }, 100);
  });
</script>

<style lang="less">
  .t-table__filter-pop-wrapper {
    .empty-item {
      position: relative;

      &::before {
        position: absolute;
        top: 0;
        right: 16px;
        left: 16px;
        height: 0;
        border-top: 1px solid #e5e5e5;
        content: '';
      }
    }
  }
</style>
