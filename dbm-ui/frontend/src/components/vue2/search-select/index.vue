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
  <div ref="searchSelectRef" />
</template>

<script lang="tsx">
  import _ from 'lodash';
  import type { PropType } from 'vue';

  import { beforeLoad, loadInstance, mount, unmount } from '@blueking/bk-weweb';

  export interface Item {
    id: string,
    name: string,
  }
  export interface SearchValue {
    id: string,
    name: string,
    values: Item[]
  }
  export interface SearchData {
    id: string,
    name: string,
    children?: Item[]
  }

  export default {
    name: 'BkSearchSelect',
  };
</script>

<script setup lang="tsx">

  const props = defineProps({
    appKey: {
      type: String,
      default: 'search-select',
    },
    modelValue: {
      type: Array as PropType<SearchValue[]>,
      default: () => [],
    },
    data: {
      type: Array as PropType<SearchData[]>,
      default: () => [],
    },
    // eslint-disable-next-line vue/no-unused-properties
    placeholder: {
      type: String,
      default: '请输入',
    },
    // eslint-disable-next-line vue/no-unused-properties
    clearable: {
      type: Boolean,
      default: true,
    },
    // eslint-disable-next-line vue/no-unused-properties
    showCondition: {
      type: Boolean,
      default: false,
    },
    // ----- 自定义属性 -------
    // data 是否可重复选择
    isRepeat: {
      type: Boolean,
      default: false,
    },
    // 是否允许自定义输入内容
    isCustom: {
      type: Boolean,
      default: false,
    },
  });

  const emit = defineEmits([
    'change',
    'clear',
    'update:modelValue',
  ]);

  const searchSelectRef = ref<HTMLDivElement>();
  const key = computed(() => props.appKey);
  const vueInstance = ref();
  const compInstance = ref();

  /**
   * 过滤已经选择类型
   */
  const filterData = computed(() => {
    if (props.isRepeat) {
      return props.data;
    }

    const selected = props.modelValue.map(value => value.id);
    return props.data.filter(item => !selected.includes(item.id));
  });

  watch(() => props.modelValue, (values) => {
    const len = values.length;
    if (props.isCustom === false && len > 0) {
      const last = values[len - 1];
      const valueIds = values.map(item => item.id);
      const conditionIds = props.data.map(item => item.id);
      const [firstId] = conditionIds;
      // 自定义输入内容默认替换成 props.data 第一个选项
      if (!conditionIds.includes(last.id)) {
        const cloneValues = _.cloneDeep(values);
        const index = valueIds.findIndex(id => id === firstId);
        const { id, name } = props.data[0];
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
        emit('update:modelValue', cloneValues);
      }
    }
    handleChangeVueData();

    // 控制 search-select 显示 popover 内容
    compInstance.value?.hidePopper();
    nextTick(() => {
      filterData.value.length > 0 && compInstance.value?.showMenu();
    });
  }, { deep: true });

  /**
   * 修改 vue2 实例数据
   */
  const handleChangeVueData = () => {
    if (vueInstance.value) {
      const { values } = vueInstance.value;
      vueInstance.value.values.splice(0, values.length, ...props.modelValue);
    }
  };


  beforeLoad();
  onMounted(async () => {
    const { VITE_PUBLIC_PATH } = window.PROJECT_ENV;
    await loadInstance({
      url: `${window.location.origin}${VITE_PUBLIC_PATH ? VITE_PUBLIC_PATH : '/'}vue2-components/search-select/index.js`,
      mode: 'js',
      id: key.value,
      container: searchSelectRef.value,
      showSourceCode: true,
      scopeCss: true,
      scopeJs: true,
    });

    mount(key.value, searchSelectRef.value, (instance, { Vue2, BkSearchSelect }: any) => {
      const div = document.createElement('div');
      searchSelectRef.value?.appendChild(div);
      vueInstance.value = new Vue2({
        el: div,
        components: {
          SearchSelect: BkSearchSelect,
        },
        data() {
          return {
            values: [],
          };
        },
        render(h: any) {
          return h('SearchSelect', {
            props: {
              ...props,
              data: filterData.value,
              values: this.values,
            },
            on: {
              change: (values: any[]) => {
                emit('update:modelValue', values);
                emit('change', values);
              },
              clear: () => {
                emit('update:modelValue', []);
                emit('clear');
              },
            },
          });
        },
      });
      [compInstance.value] = vueInstance.value.$children;
      handleChangeVueData();
    });
  });

  onBeforeUnmount(() => {
    unmount(key.value);
  });
</script>

<style lang="less" scoped>
:deep(.bk-search-select) {
  width: 100%;
  background: white;
}
</style>
