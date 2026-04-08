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
  <span
    class="db-status"
    :class="[`db-status-${type}`, `db-status-${type}--${theme}`]">
    <BkLoading
      v-if="isLoading"
      loading
      mode="spin"
      size="mini"
      theme="primary" />
    <span
      v-else
      class="db-status-dot" />
    <slot />
  </span>
</template>

<script setup lang="ts">
  interface Props {
    theme?: 'default' | 'warning' | 'success' | 'danger' | 'loading' | string;
    type?: 'fill' | 'linear' | string;
  }

  defineOptions({
    name: 'DbStatus',
  });

  const props = withDefaults(defineProps<Props>(), {
    theme: 'default',
    type: 'fill',
  });

  const isLoading = computed(() => props.theme === 'loading');
</script>

<style lang="less" scoped>
  :deep(.bk-loading-size-mini) {
    margin-right: 8px;
  }

  .db-status {
    display: inline-flex;
    align-items: center;
    vertical-align: middle;

    .db-status-dot {
      margin-right: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    &.db-status-fill {
      .db-status-dot {
        width: 12px;
        height: 12px;
        background-color: @bg-default;
        border: 3px solid @border-disable;
      }

      &.db-status-fill--warning .db-status-dot {
        background-color: @bg-warning;
        border-color: #ffe8c3;
      }

      &.db-status-fill--success .db-status-dot {
        background-color: @bg-success;
        border-color: #dcffe2;
      }

      &.db-status-fill--danger .db-status-dot {
        background-color: @bg-danger;
        border-color: #fdd;
      }
    }

    &.db-status-linear {
      .db-status-dot {
        width: 8px;
        height: 8px;
        background-color: @bg-dark-gray;
        border: 1px solid @border-light-gray;
      }

      &.db-status-linear--warning .db-status-dot {
        background-color: #ffe8c3;
        border-color: @border-warning;
      }

      &.db-status-linear--success .db-status-dot {
        background-color: #e5f6ea;
        border-color: @border-success;
      }

      &.db-status-linear--danger .db-status-dot {
        background-color: #fdd;
        border-color: @border-danger;
      }
    }

    &.db-status-fill--loading,
    &.db-status-linear--loading {
      background-color: transparent;
      border: none;

      .bk-loading-wrapper {
        display: flex;
        font-size: 0;
      }
    }
  }
</style>
