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
  <div class="instance-selector-panel-tab">
    <div
      v-for="item in panelList"
      :key="item.id"
      class="tab-item"
      :class="{
        active: modelValue === item.id,
      }"
      @click="handleClick(item.id)">
      {{ item.title }}
    </div>
  </div>
</template>

<script lang="ts">
  import type { InjectionKey, Ref } from 'vue';

  import { t } from '@locales/index';

  export const defaultPanelList = [
    {
      id: 'tendbha',
      title: t('主从'),
    },
    {
      id: 'tendbsingle',
      title: t('单节点'),
    },
    {
      id: 'manualInput',
      title: t('手动输入'),
    },
  ];
  export type PanelTypes = {
    id: string;
    title: string;
  };
  export const activePanelInjectionKey: InjectionKey<Ref<PanelTypes['id']>> = Symbol('activePanel');
</script>

<script setup lang="ts">
  interface Props {
    modelValue: string;
    panelList?: Array<PanelTypes>;
  }
  interface Emits {
    (e: 'update:modelValue', value: string): void;
  }

  const props = defineProps<Props>();
  const emits = defineEmits<Emits>();

  const handleClick = (tab: string) => {
    if (props.modelValue === tab) {
      return;
    }
    emits('update:modelValue', tab);
  };
</script>
<style lang="less">
  .instance-selector-panel-tab {
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
