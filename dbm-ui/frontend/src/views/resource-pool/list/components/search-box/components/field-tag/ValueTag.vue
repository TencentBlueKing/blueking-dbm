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
  <div class="value-tag">
    <div>{{ config.label }}</div>
    <div style="padding: 0 4px;">
      =
    </div>
    <div>{{ renderText }}</div>
    <DbIcon
      class="remove-btn"
      type="close"
      @click="handleRemove" />
  </div>
</template>
<script setup lang="ts">
  import _ from 'lodash';
  import { computed } from 'vue';

  import fieldConfig from '../field-config';

  interface Props {
    name: string;
    value: any
  }

  interface Emits{
    (e: 'remove', name: string): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const config = fieldConfig[props.name];

  const renderText = computed(() => {
    if (_.isEmpty(props.value)) {
      return '--';
    }

    return props.value;
  });

  const handleRemove = () => {
    emits('remove', props.name);
  };
</script>
<style lang="less" scoped>
  .value-tag {
    display: flex;
    height: 22px;
    padding: 0 6px;
    font-size: 12px;
    line-height: 22px;
    color: #63656e;
    background: #f0f1f5;
    border-radius: 2px;
    align-items: center;

    &:hover {
      background: #dcdee5;
    }

    & ~ .value-tag {
      margin-left: 6px;
    }

    .remove-btn {
      padding-top: 2px;
      padding-left: 4px;
      font-size: 16px;
      cursor: pointer;
    }
  }
</style>
