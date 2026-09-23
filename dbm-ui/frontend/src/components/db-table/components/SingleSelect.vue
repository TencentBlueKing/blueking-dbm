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
    <div class="t-table__filter-pop-search">
      <Input
        v-model="filterKey"
        autofocus
        borderless
        clearable
        :placeholder="t('请输入关键字')">
        <template #prefix-icon> <SearchIcon /></template>
      </Input>
    </div>
    <BkLoading
      :loading="isRemoteListLoading"
      style="width: 100%">
      <div
        ref="wrapper"
        class="t-table__filter-pop-wrapper"
        style="width: 100%">
        <RadioGroup
          v-model="localValue"
          style="width: 100%"
          @change="handleChange">
          <div
            v-for="item in renderList"
            :key="item.value"
            class="t-table__filter-pop-item">
            <Radio
              :label="item.label"
              :value="item.value" />
          </div>
        </RadioGroup>
      </div>
    </BkLoading>
    <div
      v-if="filterKey && renderList.length < 1 && !isRemoteListLoading"
      class="t-table__filter-pop-search-empty">
      {{ t('未搜索到 “{n}” 相关数据', { n: filterKey }) }}
    </div>
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { SearchIcon } from 'tdesign-icons-vue-next';
  import { Input, Radio, RadioGroup, type RadioValue } from 'tdesign-vue-next';
  import { useI18n } from 'vue-i18n';

  import { makeMap } from '@utils';

  import useMenuList from './hooks/useMenuList';

  interface Props {
    // eslint-disable-next-line vue/no-unused-properties
    list?: {
      label: string;
      value: number | string;
    }[];

    remoteMethod?: (params: {
      defaultValue?: string;
      keyword?: string;
    }) => Promise<{ label: string; value: number | string }[]>;
    // eslint-disable-next-line vue/no-unused-properties
    remoteSearch?: boolean;
    value?: number | string;
  }

  type Emits = (e: 'change', value: RadioValue) => void;

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
  const localValue = shallowRef(props.value);
  const contentMinWidth = ref(0);

  const renderList = computed(() => {
    const keyword = `${filterKey.value || ''}`.trim().toLowerCase();
    if (!keyword) {
      const modelValueMap = makeMap(defaultValue.value.map((item) => item.value));
      return [...defaultValue.value, ..._.filter(list.value, (item) => !modelValueMap[item.value])];
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
          defaultValue: String(props.value),
        }).then((data) => {
          defaultValue.value = data;
        });
      }
    },
    {
      immediate: true,
    },
  );

  const handleChange = (value: RadioValue) => {
    emits('change', value);
  };
</script>
