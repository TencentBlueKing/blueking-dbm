<!--
 * TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
 *
 * Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
 *
 * Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
 * You may obtain a copy of the License athttps://opensource.org/licenses/MIT
 *
 * Unless required by applicable law or agreed to in writing, software distributed under the License is distributed
 * on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for
 * the specific language governing permissions and limitations under the License.
-->

<template>
  <BkSearchSelect
    v-model:model-value="modelValues"
    :conditions="conditions"
    :data="data"
    unique-select
    value-behavior="need-key"
    value-split-code=","
    v-bind="$attrs" />
</template>

<script setup lang="ts">
  import type { SearchSelect } from 'bkui-vue';
  import _ from 'lodash';

  import { useUrlSearch } from '@hooks';

  type SearchSelectProps = InstanceType<typeof SearchSelect>['$props'];

  interface Props {
    data: SearchSelectProps['data'],
    conditions?: SearchSelectProps['conditions'],
    parseUrl?: boolean, // 是否从 URL 上面解析搜索值
  }

  interface Emits {
    (e: 'change', value: SearchSelectProps['modelValue']): void,
  }

  const props = withDefaults(defineProps<Props>(), {
    conditions: () => [],
    parseUrl: true,
  });

  const emits = defineEmits<Emits>();

  const { getSearchParams } = useUrlSearch();

  const getDefaultValue = () => {
    const initValues = modelValues.value ?? [];
    if (!props.parseUrl) {
      return initValues;
    }
    const searchParams = getSearchParams();
    const defaultValue: SearchSelectProps['modelValue'] = [];
    props.data?.forEach((item) => {
      if (_.has(searchParams, item.id)) {
        const searchValue = searchParams[item.id];
        const child = (item.children || []).find(child => child.id === searchValue);
        defaultValue.push({
          ...item,
          values: [
            {
              id: searchValue,
              name: child?.name ?? searchValue,
            },
          ],
        });
      }
    });
    // 保留初始化时传入的 modelValues
    return defaultValue.length > 0 ? defaultValue : initValues;
  };

  const modelValues = defineModel<SearchSelectProps['modelValue']>({
    default: [],
  });

  onMounted(() => {
    modelValues.value = getDefaultValue();
  });

  watch(modelValues, (values, oldValues) => {
    // 处理组件触发键盘删除时即时为空也会返回新的[]导致一直触发change
    if (oldValues && values?.length === 0 && oldValues?.length === 0) {
      return;
    }

    nextTick(() => {
      emits('change', modelValues.value);
    });
  }, { immediate: true, deep: true });
</script>

<style lang="less" scoped>
  .bk-search-select {
    background-color: white;
  }
</style>
