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
  <div class="machine-resource-selector-panel-tab">
    <div
      v-for="item in panelList"
      :key="item.id"
      class="tab-item"
      :class="{
        active: modelValue === item.id,
      }"
      @click="() => handleClick(item.id)">
      {{ item.name }}
    </div>
  </div>
</template>
<script setup lang="ts">
  interface Props {
    panelList: {
      id: string;
      name: string;
    }[];
  }

  defineProps<Props>();

  const modelValue = defineModel<string>({
    required: true,
  });

  const handleClick = (id: string) => {
    modelValue.value = id;
  };
</script>
<style lang="less">
  @import '@styles/mixins.less';

  .machine-resource-selector-panel-tab {
    height: 42px;
    font-size: @font-size-mini;
    line-height: 42px;
    background-color: #fafbfd;
    border-bottom: 1px solid @border-disable;
    .flex-center();

    .tab-item {
      min-width: 200px;
      margin-bottom: -1px;
      text-align: center;
      cursor: pointer;
      border: 1px solid @border-disable;
      border-top: 0;
      border-left: 0;
      border-bottom-color: transparent;

      &.active {
        background-color: @bg-white;
        border-bottom-color: @border-white;
      }

      &.disabled {
        color: #c4c6cc;
        cursor: not-allowed;
      }

      & ~ .tab-item {
        border-left: 1px solid #dcdee5;
      }
    }
  }
</style>
