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
      class="db-status__dot" />
    <slot />
  </span>
</template>
<script lang="ts">
  export default {
    name: 'DbStatus',
  };
</script>

<script setup lang="ts">
  interface Props {
    theme?: 'default' | 'warning' | 'success' | 'danger' | 'loading' | string,
    type?: 'fill' | 'linear' | string,
  }

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

    .db-status__dot {
      margin-right: 8px;
      border-radius: 50%;
      flex-shrink: 0;
    }

    &-fill {
      .db-status__dot {
        width: 12px;
        height: 12px;
        background-color: @bg-default;
        border: 3px solid @border-disable;
      }

      &--warning .db-status__dot {
        background-color: @bg-warning;
        border-color: #ffe8c3;
      }

      &--success .db-status__dot {
        background-color: @bg-success;
        border-color: #dcffe2;
      }

      &--danger .db-status__dot {
        background-color: @bg-danger;
        border-color: #fdd;
      }
    }

    &-linear {
      .db-status__dot {
        width: 8px;
        height: 8px;
        background-color: @bg-dark-gray;
        border: 1px solid @border-light-gray;
      }

      &--warning .db-status__dot {
        background-color: #ffe8c3;
        border-color: @border-warning;
      }

      &--success .db-status__dot {
        background-color: #e5f6ea;
        border-color: @border-success;
      }

      &--danger .db-status__dot {
        background-color: #fdd;
        border-color: @border-danger;
      }
    }

    &-fill--loading,
    &-linear--loading {
      background-color: transparent;
      border: none;

      .bk-loading-wrapper {
        display: flex;
        font-size: 0;
      }
    }
  }
</style>
