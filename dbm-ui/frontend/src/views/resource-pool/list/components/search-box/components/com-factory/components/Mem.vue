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
  <div class="search-item-mem">
    <BkInput
      v-model="min"
      :min="1"
      type="number"
      @change="handleChange" />
    <div class="ml-12 mr-12">
      至
    </div>
    <BkInput
      v-model="max"
      type="number"
      @change="handleChange" />
  </div>
</template>
<script setup lang="ts">
  import {
    ref,
    watch,
  } from 'vue';

  interface Props {
    defaultValue?: [number, number]
  }
  interface Emits {
    (e: 'change', value: Props['defaultValue']): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();
  defineOptions({
    inheritAttrs: false,
  });
  const min = ref();
  const max = ref();

  watch(() => props.defaultValue, () => {
    if (props.defaultValue) {
      [min.value, max.value] = props.defaultValue;
    } else {
      min.value = '';
      max.value = '';
    }
  }, {
    immediate: true,
  });

  const handleChange = () => {
    emits('change', [min.value, max.value]);
  };
</script>
<style lang="less">
  .search-item-mem {
    display: flex;
    align-items: center;
  }
</style>
