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
        :key="renderKey"
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
  import { computed, onMounted, ref } from 'vue';

  import fieldConfig from './components/field-config';
  import FieldInput from './components/field-input/Index.vue';
  import FieldTag from './components/field-tag/Index.vue';
  import { isValueEmpty } from './components/utils';

  interface Emits {
    (e: 'change', value: Record<string, any>): void;
  }
  interface Expose {
    clearValue: () => void;
  }

  const emits = defineEmits<Emits>();

  const route = useRoute();

  const comMap = {
    input: FieldInput,
    tag: FieldTag,
  } as Record<string, any>;

  const renderStatus = ref('input');
  const searchParams = ref<Record<string, any>>({});
  const renderKey = ref(0);

  const renderCom = computed(() => comMap[renderStatus.value]);

  // 切换搜索展示样式
  const handleToggle = () => {
    renderStatus.value = renderStatus.value === 'input' ? 'tag' : 'input';
  };

  // 解析 url 上面附带的查询参数
  const parseUrlParams = () => {
    Object.keys(route.query).forEach((fieldName) => {
      const config = fieldConfig[fieldName as keyof typeof fieldConfig];
      const value = route.query[fieldName] as string;

      if (!config) {
        return;
      }

      if (value === '') {
        delete searchParams.value[fieldName];
        return;
      }

      const typeHandlers = {
        array: () => value.split(','),
        rang: () => value.split('-'),
        number: () => Number(value),
        string: () => value,
      };

      searchParams.value[fieldName] = typeHandlers[config.type]();
    });
  };

  // 提交搜索
  const handleSubmit = () => {
    const params = Object.entries(fieldConfig).reduce<Record<string, any>>((acc, [fieldName, config]) => {
      const value = searchParams.value[fieldName];

      if (isValueEmpty(value)) {
        return acc;
      }

      if (config.type === 'array' && value.length > 0) {
        acc[fieldName] = value.join(',');
      } else if (config.type === 'rang' && value.length > 0) {
        acc[fieldName] = `${value[0]}-${value[1]}`;
      } else {
        acc[fieldName] = value;
      }

      return acc;
    }, {});

    emits('change', params);
  };

  onBeforeMount(() => {
    parseUrlParams();
  });

  onMounted(() => {
    handleSubmit();
  });

  onActivated(() => {
    renderKey.value += 1;
    parseUrlParams();
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
    padding: 20px 0;
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
