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
    v-bind="$attrs"
    v-model:model-value="modelValues"
    :conditions="conditions"
    :data="data" />
</template>

<script setup lang="ts">
  import type { SearchSelect } from 'bkui-vue';
  import _ from 'lodash';

  import { useUrlSearch } from '@hooks';

  type SearchSelectProps = InstanceType<typeof SearchSelect>['$props'];

  interface Props {
    modelValue: SearchSelectProps['modelValue'],
    data: SearchSelectProps['data'],
    conditions?: SearchSelectProps['conditions'],
    isCustom?: boolean, // 是否允许自定义输入
    parseUrl?: boolean, // 是否从 URL 上面解析搜索值
  }

  interface Emits {
    (e: 'change', value: SearchSelectProps['modelValue']): void,
    (e: 'update:modelValue', value: SearchSelectProps['modelValue']): void,
  }

  const props = withDefaults(defineProps<Props>(), {
    modelValue: () => [],
    conditions: () => [],
    isCustom: false,
    parseUrl: true,
  });

  const emits = defineEmits<Emits>();

  const { getSearchParams } = useUrlSearch();

  const getDefaultValue = () => {
    if (!props.parseUrl) {
      return [];
    }
    const searchParams = getSearchParams();
    const defaultValue: SearchSelectProps['modelValue'] = [];
    props.data?.forEach((item) => {
      if (_.has(searchParams, item.id)) {
        const searchValue = searchParams[item.id];
        defaultValue.push({
          ...item,
          values: [
            {
              id: searchValue,
              name: searchValue,
            },
          ],
        });
      }
    });
    return defaultValue;
  };

  let isInit = false;
  // 是否从组件内部更改
  const isChangeFromWhitin = ref(true);
  const modelValues = ref<SearchSelectProps['modelValue']>(getDefaultValue());

  watch(() => props.modelValue, (modelValue) => {
    if (!isInit && props.parseUrl) {
      isInit = true;
      if (modelValues.value?.length) {
        return;
      }
    }

    isChangeFromWhitin.value = false;
    modelValues.value = modelValue;
    nextTick(() => {
      isChangeFromWhitin.value = true;
    });
  }, { immediate: true, deep: true });

  watch(() => modelValues, (value) => {
    if (isChangeFromWhitin.value === false) return;

    const values = value.value;
    const data = props.data || [];
    if (values) {
      const len = values.length;
      // 不支持自定义 data items
      if (props.isCustom === false && len > 0) {
        const last = values[len - 1];
        const valueIds = values.map(item => item.id);
        const conditionIds = data.map(item => item.id);
        const [firstId] = conditionIds;
        // 自定义输入内容默认替换成 props.data 第一个选项
        if (!conditionIds.includes(last.id)) {
          const cloneValues = _.cloneDeep(values);
          const index = valueIds.findIndex(id => id === firstId);
          const { id, name } = data[0] || {};
          const item = {
            id,
            name,
            values: [{
              id: last.id,
              name: last.id,
            }],
          };
          if (index > -1) {
            cloneValues.splice(len - 1, 1);
            cloneValues.splice(index, 1);
            cloneValues.push(item);
          } else {
            cloneValues.splice(len - 1, 1, item);
          }
          emits('update:modelValue', cloneValues);
          emits('change', cloneValues);
          return;
        }
      }
    }
    emits('update:modelValue', values);
    emits('change', values);
  }, { immediate: true, deep: true });

</script>

<style lang="less" scoped>
  .bk-search-select {
    background-color: white;
  }
</style>
