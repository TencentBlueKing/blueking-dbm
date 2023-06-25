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
  <div class="resource-pool-search-box">
    <KeepAlive>
      <Component
        :is="renderCom"
        v-model="searchParams"
        @submit="handleSubmit" />
    </KeepAlive>
    <div
      class="toggle-btn"
      @click="handleToggle">
      <DbIcon :type="renderStatus === 'input' ? 'up-big' : 'down-big'" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import {
    computed,
    onMounted,
    ref,
  } from 'vue';

  import { useUrlSearch } from '@hooks';

  import fieldConfig from './components/field-config';
  import FieldInput from './components/field-input/Index.vue';
  import FieldTag from './components/field-tag/Index.vue';
  import { isValueEmpty } from './components/utils';

  interface Emits{
    (e: 'change', value: Record<string, any>): void;
  }
  interface Expose{
    clearValue: () => void;
  }

  const emits = defineEmits<Emits>();

  const comMap = {
    input: FieldInput,
    tag: FieldTag,
  } as Record<string, any>;

  const {
    getSearchParams,
  } = useUrlSearch();
  const urlSearchParams = getSearchParams();

  const renderStatus = ref('input');
  const searchParams = ref<Record<string, any>>({});

  const renderCom = computed(() => comMap[renderStatus.value]);

  // 解析 url 上面附带的查询参数
  Object.keys(urlSearchParams).forEach((fieldName) => {
    const config = fieldConfig[fieldName as keyof typeof fieldConfig];
    if (!config) {
      return;
    }
    if (config.type === 'array') {
      searchParams.value[fieldName] = urlSearchParams[fieldName].split(',');
    } else if (config.type === 'rang') {
      searchParams.value[fieldName] = urlSearchParams[fieldName].split('-');
    } else {
      searchParams.value[fieldName] = urlSearchParams[fieldName];
    }
  });

  // 切换搜索展示样式
  const handleToggle = () => {
    renderStatus.value = renderStatus.value === 'input' ? 'tag' : 'input';
  };
  // 提交搜索
  const handleSubmit = () => {
    const result = Object.keys(searchParams.value).reduce((result, key) => {
      const value = searchParams.value[key];
      const config = fieldConfig[key];
      if (isValueEmpty(value)) {
        return result;
      }

      if (config.type === 'array' && value.length > 0) {
        return {
          ...result,
          [key]: value.join(','),
        };
      }
      if (config.type === 'rang' && value.length > 0) {
        return {
          ...result,
          [key]: `${value[0]}-${value[1]}`,
        };
      }
      return {
        ...result,
        [key]: value,
      };
    }, {} as Record<string, string>);

    emits('change', result);
  };

  onMounted(() => {
    handleSubmit();
  });

  defineExpose<Expose>({
    clearValue() {
      searchParams.value = {};
      renderStatus.value = 'input';
      handleSubmit();
    },
  });

</script>
<style lang="less">
.resource-pool-search-box {
  position: relative;
  padding: 20px;
  font-size: 12px;
  color: #63656e;
  background: #fff;
  box-shadow: 0 2px 4px 0 #1919290d;

  .toggle-btn {
    position: absolute;
    bottom: -16px;
    left: 50%;
    display: flex;
    width: 64px;
    height: 16px;
    color: #fff;
    cursor: pointer;
    background: #dcdee5;
    border-radius: 0 0 4px 4px;
    transform: translateX(-50%);
    align-items: center;
    justify-content: center;
  }
}
</style>
