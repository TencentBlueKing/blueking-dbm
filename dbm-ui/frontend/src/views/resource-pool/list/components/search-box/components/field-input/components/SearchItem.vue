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
  <div
    class="serach-item"
    :style="styles">
    <div class="wrapper">
      <div class="search-item-label">
        {{ config.label }}
      </div>
      <ComFactory
        :model="model"
        :model-value="renderValue"
        :name="name"
        @change="handleChange" />
    </div>
  </div>
</template>
<script setup lang="ts">
  import { computed } from 'vue';

  import ComFactory from '../../com-factory/Index.vue';
  import fieldConfig from '../../field-config';

  interface Props {
    name: string,
    model: Record<string, any>
  }

  interface Emits {
    (e: 'change', fieldName: string, value: any): void
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const renderValue = computed(() => props.model[props.name]);

  const config = fieldConfig[props.name];

  const styles = {
    flex: config.flex ? config.flex : 1,
  };

  const handleChange = (value: any) => {
    emits('change', props.name, value);
  };

</script>
<style lang="less" scoped>
  .serach-item {
    display: inline-block;

    & ~ .serach-item {
      .wrapper {
        padding-left: 40px;
      }
    }

    .search-item-label {
      margin-bottom: 6px;
      font-size: 12px;
      line-height: 20px;
      color: #63656e;
    }
  }
</style>
