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
  <div
    class="tip-msg-main"
    :class="{
      'is-error': isError,
      'is-warnning': !isError,
    }">
    <div class="icon-box">
      <DbIcon
        v-if="isError"
        class="tip-icon error-icon"
        type="close-circle-shape" />
      <DbIcon
        v-else
        class="tip-icon warnning-icon"
        type="alert" />
    </div>
    <div class="msg-main">{{ data }}</div>
  </div>
</template>
<script setup lang="ts">
  interface Props {
    data?: string;
    type?: string;
  }

  const props = withDefaults(defineProps<Props>(), {
    data: '',
    type: 'error',
  });

  const isError = computed(() => props.type === 'error');
</script>
<style lang="less" scoped>
  .tip-msg-main {
    display: flex;
    min-height: 40px;
    padding: 0 12px;
    margin: 0 16px;
    margin-bottom: 8px;
    cursor: pointer;
    border: 1px solid transparent;
    border-radius: 2px;
    align-items: center;

    &.is-error {
      background: #fdd9;

      &:hover {
        border-color: #f8b4b4;
      }
    }

    &.is-warnning {
      background: #ffe8c399;

      &:hover {
        border-color: #ffb848;
      }
    }

    .icon-box {
      display: flex;
      margin-right: 8px;
      align-items: center;

      .tip-icon {
        font-size: 14px;

        &.error-icon {
          color: #ea3636;
        }

        &.warnning-icon {
          color: #f59500;
        }
      }
    }

    .msg-main {
      font-size: 12px;
      color: #4d4f56;
    }
  }
</style>
