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
  <ul
    v-show="isVisible"
    class="dbm-option-group"
    :class="{
      'is-collapsible': collapsible,
      'is-disabled': disabled,
      'is-divider': isDivider,
    }">
    <div
      v-if="isDivider"
      class="dbm-option-group-divider-container">
      <BkDivider
        color="#EAEBF0"
        :style="{ margin: 0 }"
        type="solid" />
    </div>
    <li
      v-else
      class="dbm-option-group-label"
      @click="handleToggleCollapse">
      <slot name="label">
        <span class="dbm-option-group-label-content">
          <AngleUpFill
            v-if="collapsible"
            class="dbm-option-group-label-icon"
            :class="{ 'is-collapse': groupCollapse }" />
          <span class="dbm-option-group-label-title">{{ groupLabel }}</span>
        </span>
      </slot>
    </li>
    <ul
      v-show="!groupCollapse"
      class="dbm-option-group-content">
      <slot />
    </ul>
  </ul>
</template>

<script setup lang="ts">
  import { AngleUpFill } from 'bkui-vue/lib/icon';
  import type { VNode } from 'vue';

  import { optionGroupKey, type OptionRegistry, type OptionValue, selectKey } from '../common';

  interface Props {
    /** 是否折叠，仅 collapsible 开启时生效 */
    collapse?: boolean;
    /** 分组是否支持点击折叠 */
    collapsible?: boolean;
    disabled?: boolean;
    /** 分组样式，divider 时只渲染一条分割线 */
    groupStyle?: 'default' | 'divider';
    label?: string;
    visible?: boolean;
  }

  type Emits = (e: 'update:collapse', collapse: boolean) => void;

  defineOptions({
    name: 'OptionGroup',
  });

  const props = withDefaults(defineProps<Props>(), {
    collapse: false,
    collapsible: false,
    disabled: false,
    groupStyle: 'default',
    label: '',
    visible: true,
  });

  const emits = defineEmits<Emits>();

  defineSlots<{
    default?: () => VNode;
    label?: () => VNode;
  }>();

  const select = inject(selectKey, null);

  const optionsMap = ref(new Map<OptionValue, OptionRegistry>());
  const groupCollapse = ref(props.collapse);

  const isDivider = computed(() => props.groupStyle === 'divider');

  const visibleCount = computed(() => [...optionsMap.value.values()].filter((option) => option.visible).length);

  const groupLabel = computed(() => `${props.label} (${visibleCount.value})`);

  // 分组内选项全部被搜索过滤掉时隐藏整个分组；分组内没有选项时跟随 select 的搜索空状态
  const isVisible = computed(() => {
    if (!props.visible) {
      return false;
    }
    if (!optionsMap.value.size) {
      return !select?.isSearchEmpty;
    }
    return visibleCount.value > 0;
  });

  watch(
    () => props.collapse,
    (value) => {
      groupCollapse.value = value;
    },
  );

  provide(
    optionGroupKey,
    reactive({
      disabled: computed(() => props.disabled),
      groupCollapse,
      register: (key: OptionValue, option: OptionRegistry) => {
        optionsMap.value.set(key, option);
      },
      unregister: (key: OptionValue, option?: OptionRegistry) => {
        if (option && optionsMap.value.get(key) !== option) {
          return;
        }
        optionsMap.value.delete(key);
      },
    }),
  );

  const handleToggleCollapse = () => {
    if (!props.collapsible || props.disabled) {
      return;
    }
    groupCollapse.value = !groupCollapse.value;
    emits('update:collapse', groupCollapse.value);
  };
</script>

<style lang="less">
  .dbm-option-group {
    .dbm-option-group-divider-container {
      padding: 4px 11px;
    }

    .dbm-option-group-label {
      height: 32px;
      padding: 0 8px;
      line-height: 32px;
      color: #979ba5;
      text-align: left;
    }

    .dbm-option-group-label-content {
      display: flex;
      user-select: none;
      align-items: center;
    }

    .dbm-option-group-label-icon {
      display: flex;
      width: 12px;
      height: 12px;
      margin-right: 8px;
      transition: all 0.1s;
      align-items: center;
      justify-content: center;

      &.is-collapse {
        transform: rotate(-90deg);
      }
    }

    .dbm-select-option {
      padding-left: 24px;
    }

    &.is-collapsible {
      .dbm-option-group-label {
        cursor: pointer;
      }

      .dbm-select-option {
        padding-left: 40px;
      }
    }

    &.is-disabled {
      .dbm-option-group-label-content {
        color: #c4c6cc;
        cursor: not-allowed;
      }
    }

    &.is-divider {
      .dbm-select-option {
        padding-left: 12px;
      }

      &:first-child {
        .dbm-option-group-divider-container {
          display: none;
        }
      }
    }
  }
</style>
