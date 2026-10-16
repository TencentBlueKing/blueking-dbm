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
  <ul class="dbm-dropdown-menu">
    <slot />
  </ul>
</template>

<script setup lang="ts">
  import type { VNode } from 'vue';

  defineOptions({
    name: 'DropdownMenu',
  });

  defineSlots<{
    default?: () => VNode;
  }>();
</script>

<style lang="less">
  .dbm-dropdown-menu {
    // 最小宽度对齐触发元素，变量由 DbDropdown 在挂载与尺寸变化时写入
    min-width: var(--dbm-dropdown-reference-width, 100%);
    padding: 5px 0;
    margin: 0;
    background: #fff;
    border: 1px solid #dcdee5;
    border-radius: 2px;
    box-sizing: border-box;

    &::-webkit-scrollbar {
      width: 4px;
      height: 4px;
    }

    &::-webkit-scrollbar-thumb {
      background: #dde4eb;
      border-radius: 20px;
      box-shadow: inset 0 0 6px hsl(0deg 0% 80% / 30%);
    }
  }
</style>
