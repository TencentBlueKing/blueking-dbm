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
  <li
    class="dbm-dropdown-item"
    @click="handleClick">
    <slot />
  </li>
</template>

<script setup lang="ts">
  import type { VNode } from 'vue';

  type Emits = (e: 'click', event: MouseEvent) => void;

  defineOptions({
    name: 'DropdownItem',
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    default?: () => VNode;
  }>();

  // 不阻止冒泡：DbDropdown 依赖内容区的点击事件收起菜单
  const handleClick = (event: MouseEvent) => {
    emits('click', event);
  };
</script>

<style lang="less">
  .dbm-dropdown-item {
    display: block;
    height: 32px;
    padding: 0 16px;
    font-size: 12px;
    line-height: 33px;
    color: #63656e;
    white-space: nowrap;
    list-style: none;
    cursor: pointer;

    &:hover {
      background-color: #f5f7fa;
    }
  }
</style>
