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
  <div class="password-instance-selector-panel-tab">
    <div
      v-for="value in panelList"
      :key="value"
      class="tab-item"
      :class="{
        active: modelValue === value,
      }"
      @click="handleClick(value)">
      {{ textMap[value] }}
    </div>
  </div>
</template>

<script setup lang="ts">
  import type { PanelTypes } from '../common/types';
  import { textMap } from '../common/utils';

  interface Props {
    panelList: Array<PanelTypes>;
  }

  defineProps<Props>();
  const modelValue = defineModel<string>({
    required: true,
  });

  const handleClick = (tab: string) => {
    if (modelValue.value === tab) {
      return;
    }
    modelValue.value = tab;
  };
</script>

<style lang="less" scoped>
  .password-instance-selector-panel-tab {
    display: flex;

    .tab-item {
      display: flex;
      height: 40px;
      cursor: pointer;
      background-color: #fafbfd;
      border-bottom: 1px solid #dcdee5;
      justify-content: center;
      align-items: center;
      flex: 1;

      &.active {
        background-color: #fff;
        border-bottom-color: transparent;
      }

      & ~ .tab-item {
        border-left: 1px solid #dcdee5;
      }
    }
  }
</style>
