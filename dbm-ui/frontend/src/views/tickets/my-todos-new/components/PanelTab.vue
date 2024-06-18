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
  <div class="panel-tab">
    <div
      v-for="(item, index) in panels"
      :key="item.name"
      class="tab-item"
      :class="{
        active: modelValue === item.name,
      }"
      @click="handleClick(item, index)">
      {{ item.label }}<span v-if="item.count">({{ item.count }})</span>
    </div>
  </div>
</template>

<script lang="ts">
  export interface PanelListItem {
    name: string;
    label: string;
    count: number;
  }
</script>
<script setup lang="ts">
  interface Props {
    panels: PanelListItem[];
  }
  interface Emits {
    (e: 'change', value: PanelListItem['name'], index: number): void;
  }
  defineProps<Props>();
  const emits = defineEmits<Emits>();
  const modelValue = defineModel<string>({
    required: true,
  });
  const handleClick = (item: PanelListItem, index: number) => {
    emits('change', item.name, index);
  };
</script>

<style lang="less">
  .panel-tab {
    display: flex;
    width: 367px;
    height: 32px;
    padding: 2px;
    background: #f0f1f5;
    border-radius: 2px;

    .tab-item {
      display: flex;
      height: 24px;
      margin: 2px;
      font-size: 14px;
      line-height: 20px;
      letter-spacing: 0;
      color: #63656e;
      cursor: pointer;
      justify-content: center;
      align-items: center;
      flex: 1;

      &.active {
        color: #3a84ff;
        background-color: #fff;
        border-radius: 2px;
      }
    }
  }
</style>
